#!/usr/bin/env python3
# ======================================================================
# MROF GOD'S EYE VIEW — BOUNDED SNAPSHOT EXPORTER (a separate process)
#
# Builds the small JSON snapshot the dashboard reads. It never scans
# raw data: it reads manifests, the last 64 KB of each open stream, one
# stat() per file, the disk's free space, and the approved report files
# (audit, ledger, pilot, wave two, recovery). It writes ONLY into its
# own output folder, which it refuses to place inside the capture
# folder, and it writes the snapshot aside and moves it into place so a
# failure leaves the previous snapshot intact and marked stale.
#
# The data-permission boundary is here, before anything is written:
# every record of a session that is not EXPOSED passes through the
# allowlists below and then godseye_policy.strip_event_level, and the
# finished snapshot is scanned for event-level keys outside its
# `exposed` section. A hit refuses the write.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
"""godseye_export.py — MROF-GODSEYE-EXPORT-1.0

    python godseye_export.py --config godseye.config.json
    python godseye_export.py --capture-dir D:\\MLES_Capture --reports-dir C:\\MROF\\reports
                             --exposure-ledger <path> --out-dir C:\\MROF\\godseye_out
                             [--windows windows.json] [--synthetic]

Run it on a timer (Task Scheduler, every few minutes) or by hand. It is
bounded and read-only on the capture; it does not run the audit, the
runner or the pilot -- point --reports-dir at their output files.
"""
import argparse
import collections
import datetime as _dt
import glob
import json
import os
import re
import shutil
import sys
import time
import tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in ('..', '../mrofyt', '../mrof', '../rvmr'):
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, _p)))

import godseye_policy as GP            # noqa: E402
import godseye_registry as GR          # noqa: E402
import mles_v12_adapter as AD          # noqa: E402
import mles_v12_audit as AU            # noqa: E402
import mrofyt_levels as LV             # noqa: E402
import mrofyt_recover as RC            # noqa: E402
import mrofyt_runner as RUN            # noqa: E402  (clock helpers only)
import mrofyt_wave2 as W2              # noqa: E402  (constants only)

EXPORT_VERSION = 'MROF-GODSEYE-EXPORT-1.0'
SNAPSHOT_SCHEMA = 'MROF-GODSEYE-SNAPSHOT-1'
SNAPSHOT_NAME = 'godseye_snapshot.json'
STATUS_NAME = 'godseye_status.json'
INSTRUMENTS = ('NQ', 'MNQ')
LIVE_ROW_AGE_S = 600.0            # newest row older than this: STALE
REPORT_PATTERNS = dict(audit='audit*.json', ledger='ledger*.json',
                       pilot='pilot*.json', wave2='wave2*.json',
                       recovery='recover*.json')
# recorder counters carried into the snapshot (never prices)
MANIFEST_FIELDS = ('captureInstanceId', 'runId', 'session', 'instrument',
                   'contract', 'recorderBuild', 'closeReason',
                   'firstRecvUtc', 'lastRecvUtc', 'declaredDepth',
                   'bookType', 'gaps', 'duplicates', 'reversals',
                   'queueOverflows', 'droppedRows', 'writeErrors',
                   'reconnects', 'crossed', 'bookResets',
                   'connectionSegments', 'reconstructed', 'reconstructedBy',
                   'reconstructedAtUtc', 'firstEventSeq', 'lastEventSeq')
_Z_FEATURES = ('aggr_z', 'opp_flip_z', 'wall_z', 'post_clear_z', 'control_z',
               'delta_z', 'replenish_z', 'opp_replenish_z', 'repl10_z',
               'aggr_z_hc', 'adverse_z', 'trend_flip_z')
_EXEC_ONLY = ('replenish_z', 'opp_replenish_z', 'replenish_ratio')


class ExportError(RuntimeError):
    pass


# ---------------------------------------------------------------------
# time helpers (America/New_York with DST, via the runner's clock)
# ---------------------------------------------------------------------
def _iso(epoch):
    if epoch is None:
        return None
    return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ')


def et_local_to_utc(date_yyyymmdd, hour, minute=0):
    """UTC epoch of a wall-clock time in America/New_York on a date,
    honouring daylight saving through mrofyt_runner.et_offset."""
    d = _dt.datetime.strptime(date_yyyymmdd, '%Y%m%d')
    naive = _dt.datetime(d.year, d.month, d.day, hour, minute,
                         tzinfo=_dt.timezone.utc).timestamp()
    utc = naive - RUN.et_offset(naive + 4 * 3600)
    return naive - RUN.et_offset(utc)


def session_window_utc(session):
    """Expected recording window of a CME session label: 18:00 ET the
    day before to 17:00 ET on the day (the daily halt is 17:00-18:00)."""
    d = _dt.datetime.strptime(session, '%Y%m%d').date()
    prev = (d - _dt.timedelta(days=1)).strftime('%Y%m%d')
    return et_local_to_utc(prev, 18), et_local_to_utc(session, 17)


def market_open(epoch):
    """Globex equity-index hours: Sunday 18:00 ET to Friday 17:00 ET with
    a 17:00-18:00 ET halt each day. Exchange holidays are not modelled;
    the answer is 'scheduled open', and says so."""
    day, sod = RUN.et_parts(epoch)
    wd = _dt.datetime.strptime(day, '%Y%m%d').weekday()   # Mon=0
    if wd == 5:
        return False
    if wd == 6:
        return sod >= 18 * 3600
    if wd == 4:
        return sod < 17 * 3600
    return not (17 * 3600 <= sod < 18 * 3600)


# ---------------------------------------------------------------------
# bounded capture reads
# ---------------------------------------------------------------------
class _Meter(object):
    def __init__(self):
        self.bytes = 0
        self.files = 0

    def read_json(self, path):
        self.bytes += os.path.getsize(path)
        self.files += 1
        with open(path) as fh:
            return json.load(fh)


def _tail_rows(path, kind, n=200, meter=None):
    """The last n complete rows of a stream as dicts, from the file's
    last 64 KB. Used on the quality stream only (kinds, counters,
    identity -- never a price)."""
    names = AD.HEADERS[kind]
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as fh:
            start = max(0, size - 65536)
            fh.seek(start)
            tail = fh.read()
    except OSError:
        return []
    if meter:
        meter.bytes += len(tail)
        meter.files += 1
    lines = tail.split(b'\n')
    body = lines[:-1] if start == 0 else lines[1:-1]
    out = []
    for raw in body[-n:]:
        try:
            row = raw.rstrip(b'\r').decode().split(',')
        except UnicodeDecodeError:
            continue
        if len(row) != len(names) or row[0] != AD.SCHEMA:
            continue
        out.append(dict(zip(names, row)))
    return out


def _parse_detail(detail):
    out = {}
    for tok in (detail or '').split():
        if '=' in tok:
            k, v = tok.split('=', 1)
            out[k] = v
    return out


def _instrument_of_base(base):
    m = re.match(r'^MLES12_([^_]+)_', base)
    return m.group(1) if m else None


def collect_capture(capture_dir, policy, now, meter):
    cap = dict(path=capture_dir, readable=AU.capture_dir_alive(capture_dir),
               scanned_utc=_iso(now))
    if not cap['readable']:
        cap.update(status='UNAVAILABLE', error='capture folder cannot be '
                   'read: drive disconnected, or not that letter')
        return cap
    try:
        du = shutil.disk_usage(capture_dir)
        cap['disk'] = dict(total_bytes=du.total, free_bytes=du.free,
                           used_bytes=du.used,
                           free_frac=round(du.free / du.total, 4)
                           if du.total else None)
    except OSError as exc:
        cap['disk'] = dict(error=str(exc))
    # one stat per file; no file is opened here
    kinds = collections.Counter()
    total = 0
    newest_mtime = 0.0
    manifests = []
    try:
        with os.scandir(capture_dir) as it:
            for de in it:
                if not de.is_file():
                    continue
                try:
                    st = de.stat()
                except OSError:
                    continue
                total += st.st_size
                newest_mtime = max(newest_mtime, st.st_mtime)
                n = de.name
                if n.endswith('_RECONSTRUCTED_manifest.json'):
                    kinds['reconstructed_manifest'] += 1
                    manifests.append(de.path)
                elif n.endswith('_manifest.json') or \
                        re.search(r'_manifest.*\.json$', n):
                    kinds['manifest'] += 1
                    manifests.append(de.path)
                elif n.endswith('.csv.partial'):
                    kinds['partial'] += 1
                elif n.endswith('_RECOVERED.csv'):
                    kinds['recovered_csv'] += 1
                elif n.endswith('.csv'):
                    kinds['csv'] += 1
                elif n.endswith('.tmp'):
                    kinds['tmp'] += 1
                else:
                    kinds['other'] += 1
    except OSError as exc:
        cap.update(status='UNAVAILABLE', error=str(exc))
        return cap
    cap['files'] = dict(kinds, total_bytes=total,
                        newest_mtime_utc=_iso(newest_mtime))
    # manifests: the recorder's own account of each closed run
    runs = []
    for mp in sorted(manifests):
        try:
            man = meter.read_json(mp)
        except (OSError, ValueError) as exc:
            runs.append(dict(manifest=os.path.basename(mp),
                             error='unreadable: %s' % exc))
            continue
        rec = {k: man.get(k) for k in MANIFEST_FIELDS if k in man}
        rec['manifest'] = os.path.basename(mp)
        rec['streams'] = {k: dict(bytes=(man.get(k) or {}).get('bytes'),
                                  rows=(man.get(k) or {}).get('rows'))
                          for k in AD.STREAMS if isinstance(man.get(k), dict)}
        rec['first_recv_epoch'] = AD.iso_to_epoch(man.get('firstRecvUtc') or '')
        rec['last_recv_epoch'] = AD.iso_to_epoch(man.get('lastRecvUtc') or '')
        rec['source'] = 'reconstructed' if man.get('reconstructed') \
            else 'recorder'
        runs.append(rec)
    cap['manifest_runs'] = runs
    # runs without a manifest: the recovery tool's own classification,
    # which is the rule that must pass before it writes anything
    orphans = []
    live_by = set()
    for r in RC.find_orphan_runs(capture_dir, now):
        pr = RC.probe_run(r)
        meter.bytes += 4 * 65536
        meter.files += len(r['streams'])
        rec = dict(base=r['base'], run_id=r['run_id'], session=r['session'],
                   instrument=_instrument_of_base(r['base']),
                   partial=r['partial'], missing=r['missing'],
                   live=r.get('live'), liveness_by=r.get('liveness_by'),
                   status=pr.get('status'), bytes_total=pr.get('bytes_total'),
                   streams={k: dict(bytes=v.get('bytes'),
                                    ends_cleanly=v.get('ends_cleanly'),
                                    why=v.get('why'))
                            for k, v in (pr.get('streams') or {}).items()},
                   damaged_tail=pr.get('damaged_tail'),
                   paths={k: p for k, p in r['streams'].items()})
        if r.get('liveness_by'):
            live_by.add(r['liveness_by'])
        # the newest row by the recorder's own clock, from the tails
        stamps = [s for s in (RC.newest_recv(p, k)
                              for k, p in r['streams'].items())
                  if s is not None]
        rec['newest_row_epoch'] = max(stamps) if stamps else None
        rec['newest_row_utc'] = _iso(rec['newest_row_epoch'])
        # the quality tail: identity, heartbeat counters, connection
        qp = r['streams'].get('quality')
        if qp:
            rows = _tail_rows(qp, 'quality', 200, meter)
            rec['quality_tail'] = _summarise_quality(rows)
        orphans.append(rec)
    cap['runs_without_manifest'] = orphans
    cap['liveness_by'] = sorted(live_by)
    cap['market_scheduled_open'] = market_open(now)
    cap['instruments'] = {i: _instrument_status(i, runs, orphans, now, cap)
                          for i in INSTRUMENTS}
    worst = [cap['instruments'][i]['status'] for i in INSTRUMENTS]
    order = ['UNAVAILABLE', 'DISCONNECTED', 'UNKNOWN', 'STALE', 'IDLE', 'LIVE']
    cap['status'] = min(worst, key=lambda s: order.index(s)
                        if s in order else 0)
    return cap


def _summarise_quality(rows):
    kinds = collections.Counter(r.get('kind', '').strip() for r in rows)
    last = rows[-1] if rows else {}
    hb = None
    for r in reversed(rows):
        if r.get('kind', '').strip() == 'HEARTBEAT':
            hb = r
            break
    conn = [r for r in rows if r.get('kind', '').strip() in
            ('DISCONNECT', 'RECONNECT', 'BOOK_RESYNC_START', 'BOOK_READY')]
    out = dict(rows=len(rows), kinds=dict(kinds),
               identity=dict(captureInstanceId=last.get('captureInstanceId'),
                             runId=last.get('runId'),
                             segId=last.get('segId'),
                             session=last.get('session'),
                             instrument=last.get('instrument'),
                             contract=last.get('contract')),
               last_row_utc=last.get('tRecvUtc'),
               last_connection_events=[
                   dict(utc=r.get('tRecvUtc'), kind=r.get('kind', '').strip(),
                        detail=(r.get('detail') or '')[:80])
                   for r in conn[-5:]])
    if hb:
        d = _parse_detail(hb.get('detail'))
        # the recorder's own counter names are terse; spelled out here so
        # no key collides with an event-level field name
        names = dict(q='quote_rows', t='trade_rows', dBid='depth_bid_rows',
                     dAsk='depth_ask_rows', qDepth='queue_depth',
                     qHigh='queue_high_water', ovf='overflows',
                     drop='dropped_rows', werr='write_errors', seg='seg',
                     runId='run_id', bookReady='book_ready')
        out['heartbeat'] = dict(utc=hb.get('tRecvUtc'),
                                counters={names.get(k, 'x_' + k): v
                                          for k, v in d.items()},
                                book_ready=d.get('bookReady') == '1',
                                write_errors=d.get('werr'),
                                dropped=d.get('drop'),
                                overflows=d.get('ovf'))
    return out


def _instrument_status(inst, runs, orphans, now, cap):
    """LIVE / IDLE / STALE / DISCONNECTED / UNAVAILABLE / UNKNOWN for one
    instrument, with the evidence that decided it."""
    mine_o = [o for o in orphans if o.get('instrument') == inst]
    mine_m = [r for r in runs if r.get('instrument') == inst]
    live = [o for o in mine_o if o.get('live')]
    latest_m = max(mine_m, key=lambda r: r.get('last_recv_epoch') or 0,
                   default=None)
    out = dict(instrument=inst, status='UNKNOWN', evidence=[],
               open_run=None,
               last_closed_run=None if latest_m is None else dict(
                   run_id=latest_m.get('runId'), session=latest_m.get('session'),
                   contract=latest_m.get('contract'),
                   build=latest_m.get('recorderBuild'),
                   close_reason=latest_m.get('closeReason'),
                   last_recv_utc=latest_m.get('lastRecvUtc'),
                   source=latest_m.get('source')))
    if live:
        o = max(live, key=lambda x: x.get('newest_row_epoch') or 0)
        direct = (o.get('liveness_by') or '').startswith('windows')
        age = None if o.get('newest_row_epoch') is None else \
            now - o['newest_row_epoch']
        qt = o.get('quality_tail') or {}
        ident = qt.get('identity') or {}
        out['open_run'] = dict(
            run_id=o['run_id'], session=o['session'],
            contract=ident.get('contract'), seg=ident.get('segId'),
            capture_instance=ident.get('captureInstanceId'),
            build=_build_for(o, runs),
            newest_row_utc=o.get('newest_row_utc'),
            newest_row_age_s=None if age is None else round(age, 1),
            held_by_recorder=direct, liveness=o.get('live'),
            heartbeat=qt.get('heartbeat'),
            last_connection_events=qt.get('last_connection_events'),
            bytes_total=o.get('bytes_total'))
        out['evidence'].append(o.get('live'))
        if age is not None and age < LIVE_ROW_AGE_S:
            out['status'] = 'LIVE'
        elif cap.get('market_scheduled_open') is False:
            out['status'] = 'IDLE'
            out['evidence'].append('no new rows, and the market is '
                                   'scheduled closed: expected')
        else:
            out['status'] = 'STALE'
            out['evidence'].append('the recorder holds the run but its '
                                   'newest row is %s old while the market '
                                   'is scheduled open'
                                   % ('unknown' if age is None
                                      else '%d s' % age))
        out['certainty'] = ('Windows file-sharing check' if direct else
                            'indirect signs only (no Windows check '
                            'available here)')
        return out
    # no run the recorder holds
    if any((o.get('live') or '').startswith('could not ask') for o in mine_o):
        out['status'] = 'UNKNOWN'
        out['evidence'].append('Windows could not be asked whether the '
                               'recorder holds a run')
        return out
    if mine_o or mine_m:
        out['status'] = 'DISCONNECTED'
        out['evidence'].append('no run is held open by the recorder for '
                               '%s; last closed run %s' %
                               (inst, (out['last_closed_run'] or {}).get(
                                   'last_recv_utc')))
        if mine_o:
            out['evidence'].append('%d run(s) without a manifest, none '
                                   'being written' % len(mine_o))
    else:
        out['evidence'].append('no run of %s in the capture folder' % inst)
    return out


def _build_for(orphan, runs):
    inst = orphan['run_id'].rsplit('-R', 1)[0]
    for r in runs:
        if r.get('captureInstanceId') == inst and r.get('recorderBuild'):
            return r['recorderBuild']
    mine = [r for r in runs if r.get('instrument') == orphan.get('instrument')
            and r.get('recorderBuild')]
    if mine:
        return max(mine, key=lambda r: r.get('last_recv_epoch') or 0)[
            'recorderBuild'] + ' (from the newest closed run)'
    return None


# ---------------------------------------------------------------------
# approved reports
# ---------------------------------------------------------------------
def load_reports(reports_dir, explicit, meter):
    out = {}
    for name, pat in REPORT_PATTERNS.items():
        path = (explicit or {}).get(name)
        if not path and reports_dir:
            cands = glob.glob(os.path.join(reports_dir, pat))
            cands = [c for c in cands if not c.endswith('.tmp')]
            if cands:
                path = max(cands, key=os.path.getmtime)
        rec = dict(path=path, ok=False, doc=None)
        if not path:
            rec['error'] = 'no %s report (%s) in %s' % (name, pat,
                                                         reports_dir)
        elif not os.path.exists(path):
            rec['error'] = 'not found: %s' % path
        else:
            try:
                st = os.stat(path)
                rec.update(bytes=st.st_size, mtime_utc=_iso(st.st_mtime),
                           mtime_epoch=st.st_mtime)
                rec['doc'] = meter.read_json(path)
                rec['ok'] = True
            except (OSError, ValueError) as exc:
                rec['error'] = 'unreadable: %s' % exc
        out[name] = rec
    return out


def _report_meta(rep):
    d = rep.get('doc') or {}
    ver = d.get('pilot') or d.get('runner') or d.get('recover') or \
        d.get('wave2') or ('audit' if 'runs' in d and 'info' in d else None)
    return dict(path=rep.get('path'), ok=rep.get('ok'),
                error=rep.get('error'), bytes=rep.get('bytes'),
                mtime_utc=rep.get('mtime_utc'), version=ver)


# ---------------------------------------------------------------------
# sessions timeline
# ---------------------------------------------------------------------
def _intervals_union(iv):
    iv = sorted((a, b) for a, b in iv if a is not None and b is not None
                and b > a)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _gaps(expected, covered, min_s=60.0):
    a, b = expected
    gaps = []
    cur = a
    for s, e in covered:
        if s > cur and s - cur >= min_s:
            gaps.append([cur, min(s, b)])
        cur = max(cur, e)
        if cur >= b:
            break
    if b - cur >= min_s:
        gaps.append([cur, b])
    return [g for g in gaps if g[1] > g[0]]


def _intersect(ga, gb):
    out = []
    for a0, a1 in ga:
        for b0, b1 in gb:
            lo, hi = max(a0, b0), min(a1, b1)
            if hi > lo:
                out.append([lo, hi])
    return out


def build_sessions(cap, reports, policy, now):
    """One record per session label, from manifests (recorder), audit
    (verdicts), ledger (skip reasons), recovery (orphans) and the open
    runs. Everything here is operational; per-session research counts
    live in `counts`."""
    audit = (reports['audit'].get('doc') or {})
    ledger = (reports['ledger'].get('doc') or {})
    audit_by = {}
    for r in audit.get('runs', []):
        i = r.get('info') or {}
        audit_by[(i.get('instrument'), i.get('run_id'))] = r
    ledger_by = {}
    for r in ledger.get('runs', []):
        ledger_by[(r.get('instrument'), r.get('run_id'))] = r
    sessions = collections.defaultdict(lambda: dict(
        instruments={i: dict(runs=[], coverage=[], gaps=[]) for i in INSTRUMENTS}))
    for m in cap.get('manifest_runs', []):
        if 'error' in m:
            continue
        inst, ses = m.get('instrument'), m.get('session')
        if inst not in INSTRUMENTS or not ses:
            continue
        a = audit_by.get((inst, m.get('runId')))
        led = ledger_by.get((inst, m.get('runId')))
        rec = dict(run_id=m.get('runId'), capture_instance=m.get('captureInstanceId'),
                   contract=m.get('contract'), build=m.get('recorderBuild'),
                   close_reason=m.get('closeReason'), source=m.get('source'),
                   first_recv_utc=m.get('firstRecvUtc'),
                   last_recv_utc=m.get('lastRecvUtc'),
                   first_recv_epoch=m.get('first_recv_epoch'),
                   last_recv_epoch=m.get('last_recv_epoch'),
                   streams=m.get('streams'),
                   recorder_counters={k: m.get(k) for k in (
                       'gaps', 'duplicates', 'droppedRows', 'writeErrors',
                       'reconnects', 'bookResets', 'queueOverflows')
                       if k in m},
                   reconstructed_by=m.get('reconstructedBy'),
                   manifest=m.get('manifest'))
        if a:
            i = a.get('info') or {}
            rec['audit'] = dict(ok=a.get('ok'),
                                failure_codes=sorted({c for c, _ in
                                                      a.get('failures', [])}),
                                rows=i.get('events'), seq_first=i.get('seq_first'),
                                seq_last=i.get('seq_last'),
                                disconnects=i.get('disconnects'),
                                book_ready=i.get('book_ready'),
                                book_resync_starts=i.get('book_resync_starts'),
                                spurious_book_ready=i.get('spurious_book_ready'),
                                depth_rows=i.get('depth_rows'),
                                depth_sides=i.get('depth_sides'),
                                depth_actions=i.get('depth_actions'),
                                latency_ms=i.get('latency_ms'),
                                suppressed_rows=i.get('suppressed_rows'))
        else:
            rec['audit'] = dict(ok=None, note='not in the audit report')
        if led:
            rec['ingest'] = dict(skipped=led.get('skipped'),
                                 rows_ingested=led.get('events'),
                                 reason=led.get('missing') or led.get('truncated')
                                 or led.get('error'))
        else:
            rec['ingest'] = dict(skipped=None, note='not in the ledger')
        sessions[ses]['instruments'][inst]['runs'].append(rec)
    for o in cap.get('runs_without_manifest', []):
        inst, ses = o.get('instrument'), o.get('session')
        if inst not in INSTRUMENTS or not ses:
            continue
        sessions[ses]['instruments'][inst]['runs'].append(dict(
            run_id=o['run_id'], source='open' if o.get('live') else 'orphan',
            live=o.get('live'), recovery_status=o.get('status'),
            newest_row_utc=o.get('newest_row_utc'),
            bytes_total=o.get('bytes_total'), partial=o.get('partial'),
            missing_streams=o.get('missing'),
            audit=dict(ok=None, note='no manifest: not auditable'),
            ingest=dict(skipped=True, note='no manifest: not ingestible')))
    overlaps = (audit.get('info') or {}).get('overlaps') or {}
    out = []
    for ses in sorted(sessions):
        s = sessions[ses]
        exp0, exp1 = session_window_utc(ses)
        exp1c = min(exp1, now)
        rec = dict(session=ses, session_class=policy.session_class(ses),
                   expected_utc=[_iso(exp0), _iso(exp1)],
                   expected_epoch=[exp0, exp1],
                   expected_clipped_to_now=exp1c < exp1,
                   instruments={})
        allg = {}
        for inst in INSTRUMENTS:
            d = s['instruments'][inst]
            iv = [(r.get('first_recv_epoch'), r.get('last_recv_epoch'))
                  for r in d['runs'] if r.get('first_recv_epoch')]
            cov = _intervals_union(iv)
            gaps = _gaps((exp0, exp1c), cov) if exp1c > exp0 else []
            covered_s = sum(b - a for a, b in cov)
            allg[inst] = gaps
            rec['instruments'][inst] = dict(
                runs=sorted(d['runs'], key=lambda r: r.get('first_recv_epoch')
                            or 0),
                coverage=[[_iso(a), _iso(b)] for a, b in cov],
                coverage_epoch=cov, covered_s=round(covered_s, 1),
                expected_s=round(max(exp1c - exp0, 0), 1),
                covered_frac=round(covered_s / (exp1c - exp0), 4)
                if exp1c > exp0 else None,
                gaps=[[_iso(a), _iso(b)] for a, b in gaps],
                gaps_epoch=gaps,
                gap_s=round(sum(b - a for a, b in gaps), 1))
        shared = _intersect(allg['NQ'], allg['MNQ'])
        rec['shared_gaps'] = [[_iso(a), _iso(b)] for a, b in shared]
        rec['shared_gap_s'] = round(sum(b - a for a, b in shared), 1)
        ov = overlaps.get(ses)
        rec['pair_overlap_frac'] = ov.get('overlap_frac') if ov else None
        rec['pair_note'] = ('overlap is measured on the hours BOTH recorded, '
                            'so it cannot see a shared gap; 1.000 does not '
                            'mean a complete session')
        out.append(rec)
    return out


# ---------------------------------------------------------------------
# hypothesis readiness (from reports; never recomputed from raw data)
# ---------------------------------------------------------------------
def _verify_registry():
    """Cheap self-check that the registry still describes the code. A
    mismatch marks the affected families UNRESOLVED_SPEC_MISMATCH."""
    bad = []
    if [l['id'] for l in GR.LEVELS] != list(LV.ACTIVE_LEVEL_IDS):
        bad.append('LEVELS')
    a6 = GR.by_id('A6')
    if tuple(a6['level_set']) != tuple(RUN.OPEN_LEVELS) or \
            a6['window_et'] != (9.5 * 3600, 9.75 * 3600):
        bad.append('A6')
    w = GR.by_id('W2-A4-OPEN')
    if tuple(w['level_set']) != tuple(W2.OPEN_LEVELS_W2) or \
            tuple(w['window_et']) != tuple(W2.OPEN_WINDOW_ET):
        bad.append('W2-A4-OPEN')
    if GR.by_id('W2-A4r-z15')['threshold_change']['variant'] != W2.Z15:
        bad.append('W2-A4r-z15')
    return bad


def _status_from_funnel(h, fun, ledger, pilot):
    """Headline status + breakdown for a wave-one family from the pilot's
    threshold funnel (an approved released summary)."""
    hid = h['id']
    windows = fun.get('windows', 0)
    stages = fun.get('first_failing_stage') or {}
    missing = fun.get('missing_inputs') or {}
    passed = fun.get('passed', 0)
    reasons = []
    # records, not dicts keyed by feature name, so the event-level key
    # scan can cover the whole snapshot without a false positive here
    breakdown = dict(windows=windows, passed=passed,
                     first_failing_stage=stages,
                     missing_inputs=[dict(input=k, windows=v) for k, v in
                                     sorted(missing.items(),
                                            key=lambda kv: -kv[1])],
                     fires_recorded=fun.get('fires_recorded'))
    bs = (ledger.get('baseline_sessions') or {})
    min_bs = min(bs.values()) if bs else None
    if h.get('not_wired') and set(h['not_wired']) >= set(
            i['name'] for i in h['inputs'] if i.get('role') != 'direction'
            and not i.get('wired')) and hid == 'A5':
        reasons.append('%s are passed as None by the runner; inputs can '
                       'never be complete' % ', '.join(h['not_wired']))
        return 'NOT_WIRED', reasons, breakdown
    if not windows:
        reasons.append('the pilot evaluated no decision window')
        return 'NO_QUALIFYING_OBSERVATIONS', reasons, breakdown
    if passed > 0:
        reasons.append('inputs complete and every condition held on %d '
                       'window(s); %s fire(s) recorded'
                       % (passed, fun.get('fires_recorded')))
        return 'READY', reasons, breakdown
    dom = max(stages.items(), key=lambda kv: kv[1])[0] if stages else None
    if dom == 'in_0930_0945':
        reasons.append('%d of %d windows fell outside 09:30-09:45 ET or off '
                       'an open-type level: a valid non-setup, not missing '
                       'data' % (stages[dom], windows))
        return 'CONDITION_FALSE', reasons, breakdown
    if dom == 'inputs_available':
        mi = max(missing.items(), key=lambda kv: kv[1])[0] if missing else None
        if mi in h.get('not_wired', []):
            reasons.append('%s is passed as None (not wired)' % mi)
            return 'NOT_WIRED', reasons, breakdown
        if mi in _EXEC_ONLY:
            reasons.append('%s is undefined on %d of %d windows because no '
                           'execution occurred at the level: a valid '
                           'non-setup by the frozen definition, not missing '
                           'data and not immaturity' % (mi, missing[mi],
                                                         windows))
            return 'NO_QUALIFYING_OBSERVATIONS', reasons, breakdown
        if mi in _Z_FEATURES:
            if min_bs is not None and min_bs < GR.BASELINE_Z['prior_sessions_min']:
                reasons.append('%s needs >= 5 prior sessions per 5-minute '
                               'bucket; the pass had only %s' % (mi, bs))
                return 'INSUFFICIENT_PRIOR_HISTORY', reasons, breakdown
            # >= 5 sessions in the pass, yet the z was None: either the
            # bucket itself had fewer than 5 prior sessions (sessions
            # cover different hours) or the baseline's dispersion was
            # zero (the frozen z returns None). The report does not say
            # which, so neither is claimed.
            reasons.append('%s was None on %d of %d windows although the '
                           'pass held %s baseline sessions: the 5-minute '
                           'bucket had fewer than 5 prior sessions, or the '
                           'baseline dispersion there was zero -- the pilot '
                           'report does not distinguish the two'
                           % (mi, missing[mi], windows, bs))
            return 'INVALID_OR_MISSING_DATA', reasons, breakdown
        reasons.append('%s missing on %d of %d windows' % (mi, missing.get(mi),
                                                          windows))
        return 'INVALID_OR_MISSING_DATA', reasons, breakdown
    reasons.append('inputs were complete on some windows and the first '
                   'failing condition was %s (%d windows): valid non-setups'
                   % (dom, stages.get(dom, 0)))
    return 'CONDITION_FALSE', reasons, breakdown


def build_hypotheses(reports, policy):
    ledger = reports['ledger'].get('doc') or {}
    pilot = reports['pilot'].get('doc') or {}
    wave2 = reports['wave2'].get('doc') or {}
    w2real = wave2.get('real') or wave2
    fun = pilot.get('step5_threshold_funnel') or {}
    feat = pilot.get('step3_feature_health') or {}
    mism = _verify_registry()
    out = []
    for h in GR.HYPOTHESES:
        rec = dict(id=h['id'], wave=h['wave'], name=h['name'],
                   registered_in=h['registered_in'],
                   implemented_in=h['implemented_in'],
                   implementation=h['implementation'],
                   mechanism=h['mechanism'], direction_rule=h['direction_rule'],
                   grid=h['grid'], window_et=h.get('window_et'),
                   level_set=h.get('level_set'),
                   inputs=h.get('inputs', []),
                   conditions=h.get('conditions', []), gate=h.get('gate', []),
                   baseline=(GR.BASELINE_Z if h.get('baseline') == 'BASELINE_Z'
                             else GR.BASELINE_RESID if h.get('baseline')
                             else None),
                   derived_from=h.get('derived_from'),
                   not_wired=h.get('not_wired', []),
                   threshold_change=h.get('threshold_change'))
        if h['id'] in mism or (h['id'] == 'A6' and 'A6' in mism):
            rec.update(status='UNRESOLVED_SPEC_MISMATCH',
                       reasons=['the registry and the frozen code disagree '
                                'about this family; see _verify_registry'])
        elif h['implementation'] == GR.CONTROL:
            src = w2real.get('arm_b') or {}
            if h['id'].startswith('ARM-B'):
                ev = src.get('evaluated_b1' if h['id'] == 'ARM-B1'
                             else 'evaluated_b2', 0)
                rec.update(status='READY' if ev else 'NO_QUALIFYING_OBSERVATIONS',
                           reasons=['%d registration(s), %d evaluated, %d '
                                    'expired (bar never closed in session)'
                                    % (src.get('registered', 0), ev,
                                       src.get('expired', 0))]
                           if src else ['no wave-two report'],
                           breakdown=src)
            else:
                rec.update(status='CONTROL',
                           reasons=['a comparison arm, not a hypothesis: '
                                    'placebo pass %s'
                                    % ('present' if wave2.get('placebo')
                                       else 'not in the wave-two report '
                                       '(run --both)')])
        elif h['wave'] == 1:
            if not reports['pilot'].get('ok'):
                rec.update(status='INVALID_OR_MISSING_DATA',
                           reasons=['no readable pilot report: %s'
                                    % reports['pilot'].get('error')])
            elif h['id'] == 'A3':
                a3 = fun.get('A3') or {}
                st = ('READY' if a3.get('fires_recorded') else
                      'CONDITION_FALSE' if a3.get('checks') else
                      'NO_QUALIFYING_OBSERVATIONS')
                rec.update(status=st, breakdown=a3,
                           reasons=['%s checks on the 2 s vacuum grid, %s '
                                    'vacuum events, %s fires' %
                                    (a3.get('checks'), a3.get('vacuum_events'),
                                     a3.get('fires_recorded'))])
            else:
                st, why, br = _status_from_funnel(h, fun.get(h['id']) or {},
                                                  ledger, pilot)
                rec.update(status=st, reasons=why, breakdown=br)
            rec['feature_availability'] = [
                dict(input=k, windows=v.get('windows'),
                     available=v.get('available'),
                     available_frac=v.get('available_frac'))
                for k, v in feat.items()
                if k in [i['name'] for i in h.get('inputs', [])]]
        else:
            if not reports['wave2'].get('ok'):
                rec.update(status='INVALID_OR_MISSING_DATA',
                           reasons=['no readable wave-two report: %s'
                                    % reports['wave2'].get('error')])
            else:
                fam = (w2real.get('families') or {}).get(h['id']) or {}
                avail = w2real.get('w2_input_availability') or {}
                nwin = w2real.get('w2_windows', 0)
                key = {'W2-A1': 'none_repl10_z', 'W2-A4f': 'none_resid_tail_5pct',
                       'W2-A4r-HC': 'none_aggr_z_hc'}.get(h['id'])
                none_n = avail.get(key) if key else None
                if fam.get('raw_fires'):
                    st = 'READY'
                    why = ['%d raw fire(s), %d distinct event(s)'
                           % (fam['raw_fires'], fam.get('distinct_events', 0))]
                elif key and nwin and none_n is not None and none_n >= nwin:
                    st = 'INSUFFICIENT_PRIOR_HISTORY'
                    why = ['%s was None on every one of %d windows: %s'
                           % (key[5:], nwin,
                              'residual fit needs >= 20 prior observations '
                              'in the bucket' if h['id'] == 'W2-A4f' else
                              'baseline needs >= 5 prior sessions in the '
                              'bucket')]
                elif nwin:
                    st = 'CONDITION_FALSE'
                    why = ['evaluated on %d windows%s; conditions did not '
                           'hold' % (nwin, '' if none_n is None else
                                     ' (%d with the new input available)'
                                     % (nwin - none_n))]
                else:
                    st = 'NO_QUALIFYING_OBSERVATIONS'
                    why = ['the wave-two pass evaluated no window']
                rec.update(status=st, reasons=why,
                           breakdown=dict(windows=nwin,
                                          input_none=none_n,
                                          raw_fires=fam.get('raw_fires'),
                                          distinct_events=fam.get(
                                              'distinct_events')))
        out.append(rec)
    for n in GR.NOT_IN_THIS_VERSION:
        out.append(dict(id=n['id'], wave=2, name=n['id'],
                        registered_in=n['registered_in'],
                        implemented_in=None, implementation=n['implementation'],
                        status='NOT_IMPLEMENTED', reasons=[n['note']]))
    return dict(registry=GR.REGISTRY_VERSION, spec_mismatch=mism,
                baselines=dict(z=GR.BASELINE_Z, resid=GR.BASELINE_RESID),
                families=out, levels=GR.LEVELS, context=GR.CONTEXT,
                discrepancies=GR.DISCREPANCIES)


# ---------------------------------------------------------------------
# released research counts (accrual), from the reports only
# ---------------------------------------------------------------------
def build_counts(reports, policy):
    pilot = reports['pilot'].get('doc') or {}
    wave2 = reports['wave2'].get('doc') or {}
    w2real = wave2.get('real') or wave2
    out = dict(rule='counts come from the released pilot and wave-two '
                    'reports and are never recomputed here; per session '
                    'they are accrual only -- no direction, time, level '
                    'or feature',
               pilot=None, wave2=None)
    if pilot:
        s6 = pilot.get('step6_frozen_signals') or {}
        dd = s6.get('dedup') or {}
        per = collections.defaultdict(lambda: collections.Counter())
        for e in dd.get('events', []):
            fam, ses = e.get('family'), e.get('session')
            if fam and ses:
                per[fam][str(ses)] += 1
        out['pilot'] = dict(
            source=_report_meta(reports['pilot']),
            sessions_inspected=pilot.get('sessions_inspected'),
            sessions_blind=pilot.get('sessions_blind'),
            blind_from=pilot.get('blind_from'),
            raw_fires_by_family=s6.get('by_family'),
            raw_fire_caveat=s6.get('raw_fire_caveat'),
            distinct_events_by_family=dd.get('distinct_events_by_family'),
            signal_source_events_by_family=dd.get(
                'signal_source_events_by_family'),
            cooldown_s=dd.get('cooldown_s'),
            distinct_events_by_family_and_session={
                f: dict(sorted(c.items())) for f, c in per.items()},
            events_withheld=(pilot.get('step7_descriptive_markouts') or {}
                             ).get('blind'))
    if w2real:
        fams = {}
        for fam, b in (w2real.get('families') or {}).items():
            fams[fam] = dict(raw_fires=b.get('raw_fires'),
                             distinct_events=b.get('distinct_events'),
                             events_visible=b.get('events_visible'),
                             events_withheld=b.get('events_withheld'),
                             signal_source_events=b.get('signal_source_events'),
                             by_session=b.get('by_session'))
        out['wave2'] = dict(source=_report_meta(reports['wave2']),
                            sessions_inspected=w2real.get('sessions_inspected'),
                            blind_from=w2real.get('blind_from'),
                            windows=w2real.get('w2_windows'),
                            input_unavailable=w2real.get('w2_input_availability'),
                            arm_b=w2real.get('arm_b'),
                            families=fams,
                            placebo_pass_present=bool(wave2.get('placebo')),
                            not_in_this_version=w2real.get(
                                'not_in_this_version'))
    return out


# ---------------------------------------------------------------------
# exposed sessions: event-level material the replay may show
# ---------------------------------------------------------------------
def build_exposed(reports, policy, windows_path, meter):
    ledger = reports['ledger'].get('doc') or {}
    wave2 = reports['wave2'].get('doc') or {}
    w2real = wave2.get('real') or wave2
    out = dict(rule='present only for sessions the exposure ledger labels '
                    'EXPOSED; the server checks the policy again on every '
                    'request', sessions={})
    fires = collections.defaultdict(list)
    for f in ledger.get('fires', []):
        if policy.may_inspect(f.get('session')):
            fires[str(f['session'])].append(dict(
                wave=1, family=f.get('family'), instrument=f.get('instrument'),
                run=f.get('run'), direction=f.get('direction'), t=f.get('t'),
                level=f.get('level'), approach=f.get('approach')))
    for f in w2real.get('fires', []):
        if policy.may_inspect(f.get('session')):
            fires[str(f['session'])].append(dict(
                wave=2, family=f.get('family'), instrument=f.get('instrument'),
                run=f.get('run'), direction=f.get('direction'), t=f.get('t'),
                level=f.get('level'), approach=f.get('approach'),
                state=f.get('state')))
    idx = {}
    winfo = dict(path=windows_path, ok=False)
    if windows_path and os.path.exists(windows_path):
        try:
            doc = meter.read_json(windows_path)
            winfo.update(ok=True, pilot=doc.get('pilot'),
                         sessions=doc.get('sessions'),
                         windows=len(doc.get('windows', [])))
            for w in doc.get('windows', []):
                ses = str(w.get('session'))
                if not policy.may_inspect(ses):
                    continue
                inst = w.get('instrument')
                # approach-level index only; the windows themselves are
                # served on demand by the server from the windows file
                ap = idx.setdefault(ses, {}).setdefault(inst, {}).setdefault(
                    str(w.get('approach_id')),
                    dict(approach_id=w.get('approach_id'),
                         level_id=w.get('level_id'), level_px=w.get('level_px'),
                         ad=w.get('ad'), t0=w.get('t_start'), run=w.get('run'),
                         family=w.get('family'), n_windows=0, t_last=None))
                ap['n_windows'] += 1
                ap['t_last'] = max(ap['t_last'] or 0, w.get('t_end') or 0)
        except (OSError, ValueError) as exc:
            winfo['error'] = str(exc)
    elif windows_path:
        winfo['error'] = 'not found'
    for ses in sorted(set(fires) | set(idx)):
        out['sessions'][ses] = dict(
            session=ses, fires=sorted(fires.get(ses, []),
                                      key=lambda x: x.get('t') or 0),
            approaches={inst: sorted(aps.values(), key=lambda a: a['t0'] or 0)
                        for inst, aps in idx.get(ses, {}).items()})
    out['windows_file'] = winfo
    return out


# ---------------------------------------------------------------------
# assemble, sanitise, write
# ---------------------------------------------------------------------
def build_snapshot(cfg, now=None):
    now = time.time() if now is None else now
    meter = _Meter()
    cap_dir = cfg['capture_dir']
    out_dir = cfg['out_dir']
    if os.path.abspath(out_dir).startswith(os.path.abspath(cap_dir) + os.sep) \
            or os.path.abspath(out_dir) == os.path.abspath(cap_dir):
        raise ExportError('out_dir must not be inside the capture folder')
    policy = GP.Policy.from_files(cfg['exposure_ledger'], cfg['blind_from'],
                                  synthetic=cfg.get('synthetic', False))
    cap = collect_capture(cap_dir, policy, now, meter)
    reports = load_reports(cfg.get('reports_dir'), cfg.get('reports'), meter)
    audit = reports['audit'].get('doc') or {}
    recov = reports['recovery'].get('doc') or {}
    snap = dict(
        schema=SNAPSHOT_SCHEMA, exporter=EXPORT_VERSION,
        generated_utc=_iso(now), generated_epoch=now,
        synthetic=bool(cfg.get('synthetic')),
        synthetic_label=('SYNTHETIC DEMONSTRATION -- every number here '
                         'comes from generated fixtures, not from the '
                         'market' if cfg.get('synthetic') else None),
        policy=policy.describe(),
        outcome_lock=GP.outcome_lock_state(cfg.get('mrof_dir') or
                                           os.path.join(HERE, '..', 'mrof')),
        health=cap,
        audit=dict(source=_report_meta(reports['audit']),
                   ok=audit.get('ok'),
                   failures_by_code=dict(collections.Counter(
                       c for c, _ in audit.get('failures', []))),
                   failures=[[c, str(d)[:200]] for c, d in
                             audit.get('failures', [])][:400],
                   open_runs_in_progress=(audit.get('info') or {}).get(
                       'open_runs_in_progress'),
                   recovery_originals_kept=len((audit.get('info') or {}).get(
                       'recovery_originals_kept') or []),
                   repair_evidence=(audit.get('info') or {}).get(
                       'repair_evidence'),
                   pair_overlaps=(audit.get('info') or {}).get('overlaps')),
        recovery=dict(source=_report_meta(reports['recovery']),
                      orphan_runs=recov.get('orphan_runs'),
                      live_runs=recov.get('live_runs'),
                      liveness_by=recov.get('liveness_by'),
                      results=[dict(run_id=r.get('run_id'),
                                    session=r.get('session'),
                                    status=r.get('status'),
                                    bytes_total=r.get('bytes_total'),
                                    written=r.get('written'),
                                    notes=r.get('notes'))
                               for r in recov.get('results', [])]),
        reports={k: _report_meta(v) for k, v in reports.items()},
        sessions=build_sessions(cap, reports, policy, now),
        hypotheses=build_hypotheses(reports, policy),
        counts=build_counts(reports, policy),
        exposed=build_exposed(reports, policy, cfg.get('windows'), meter),
    )
    # second line of defence: strip event-level keys from every record
    # section that is not the exposed one, then prove it over the WHOLE
    # document minus that section
    for k in ('health', 'audit', 'recovery', 'sessions', 'counts'):
        snap[k] = GP.strip_event_level(snap[k])
    hits = []
    for k in snap:
        if k != 'exposed':
            hits.extend(GP.scan_for_event_level(snap[k], '$.' + k))
    if hits:
        raise ExportError('refusing to write: event-level keys outside the '
                          'exposed section: %s' % hits[:10])
    for ses in snap['exposed']['sessions']:
        if not policy.may_inspect(ses):
            raise ExportError('refusing to write: %s in exposed section' % ses)
    snap['resource_use'] = dict(bytes_read=meter.bytes, files_read=meter.files)
    return snap


def write_snapshot(cfg, now=None):
    os.makedirs(cfg['out_dir'], exist_ok=True)
    snap_path = os.path.join(cfg['out_dir'], SNAPSHOT_NAME)
    status_path = os.path.join(cfg['out_dir'], STATUS_NAME)
    prev = None
    if os.path.exists(snap_path):
        try:
            with open(snap_path) as fh:
                prev = json.load(fh).get('generated_utc')
        except (OSError, ValueError):
            prev = None
    t0 = time.time()
    tracemalloc.start()
    status = dict(exporter=EXPORT_VERSION, started_utc=_iso(t0),
                  previous_snapshot_utc=prev, snapshot=snap_path)
    try:
        snap = build_snapshot(cfg, now)
        tmp = snap_path + '.tmp'
        with open(tmp, 'w') as fh:
            json.dump(snap, fh, default=str)
        os.replace(tmp, snap_path)
        status.update(ok=True, generated_utc=snap['generated_utc'],
                      bytes_read=snap['resource_use']['bytes_read'],
                      files_read=snap['resource_use']['files_read'],
                      snapshot_bytes=os.path.getsize(snap_path))
    except Exception as exc:                          # noqa: BLE001
        status.update(ok=False, error='%s: %s' % (type(exc).__name__, exc),
                      note='previous snapshot left in place and is STALE')
    finally:
        cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        status.update(duration_s=round(time.time() - t0, 3),
                      peak_python_heap_mb=round(peak / 1e6, 2),
                      finished_utc=_iso(time.time()))
        tmp = status_path + '.tmp'
        with open(tmp, 'w') as fh:
            json.dump(status, fh, indent=1)
        os.replace(tmp, status_path)
    return status


def load_config(path):
    with open(path) as fh:
        cfg = json.load(fh)
    base = os.path.dirname(os.path.abspath(path))
    for k in ('capture_dir', 'reports_dir', 'exposure_ledger', 'out_dir',
              'windows', 'mrof_dir'):
        if cfg.get(k) and not os.path.isabs(cfg[k]):
            cfg[k] = os.path.normpath(os.path.join(base, cfg[k]))
    for k, v in (cfg.get('reports') or {}).items():
        if v and not os.path.isabs(v):
            cfg['reports'][k] = os.path.normpath(os.path.join(base, v))
    cfg.setdefault('blind_from', GP.DEFAULT_BLIND_FROM)
    return cfg


def main(argv=None):
    p = argparse.ArgumentParser(description=EXPORT_VERSION)
    p.add_argument('--config')
    p.add_argument('--capture-dir')
    p.add_argument('--reports-dir')
    p.add_argument('--exposure-ledger')
    p.add_argument('--out-dir')
    p.add_argument('--windows')
    p.add_argument('--blind-from')
    p.add_argument('--synthetic', action='store_true')
    a = p.parse_args(argv)
    cfg = load_config(a.config) if a.config else {}
    for k in ('capture_dir', 'reports_dir', 'exposure_ledger', 'out_dir',
              'windows', 'blind_from'):
        v = getattr(a, k)
        if v:
            cfg[k] = v
    if a.synthetic:
        cfg['synthetic'] = True
    cfg.setdefault('blind_from', GP.DEFAULT_BLIND_FROM)
    for k in ('capture_dir', 'exposure_ledger', 'out_dir'):
        if not cfg.get(k):
            print('missing %s (config or flag)' % k)
            return 2
    st = write_snapshot(cfg)
    print(json.dumps(st, indent=1))
    return 0 if st.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
