#!/usr/bin/env python3
# ======================================================================
# MROF GOD'S EYE VIEW — LOCAL SERVER (stdlib only, read-only)
#
# Serves the static dashboard and a small JSON API over the snapshot the
# exporter wrote. It reads the snapshot and status files on each
# request (they are small), never raw data -- except the bounded replay
# endpoints, which read a short window of one exposed run through
# godseye_replay after the policy has said yes, and are refused outright
# when no exposure ledger is configured or readable.
#
# Nothing here writes: not to the capture folder, not to the reports,
# not to the exposure ledger. Binds to 127.0.0.1 unless told otherwise.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
"""godseye_server.py — MROF-GODSEYE-SERVER-1.0

    python godseye_server.py --config godseye.config.json [--port 8765] [--bind 127.0.0.1]
"""
import argparse
import collections
import glob
import json
import os
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import godseye_policy as GP            # noqa: E402
import godseye_registry as GR          # noqa: E402

SERVER_VERSION = 'MROF-GODSEYE-SERVER-1.0'
STATIC_DIR = os.path.join(HERE, 'static')
STALE_AFTER_S = 15 * 60               # a snapshot older than this is stale
BUNDLE_CACHE = 24
_MIME = {'.html': 'text/html; charset=utf-8', '.js': 'application/javascript',
         '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml',
         '.png': 'image/png', '.ico': 'image/x-icon'}


class State(object):
    """Shared, read-only view of the configured files."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.out_dir = cfg['out_dir']
        self.lock = threading.Lock()
        self._snap = (None, None)          # (mtime, doc)
        self._windows = None               # (mtime, index)
        self._bundles = collections.OrderedDict()
        self.policy = GP.Policy.from_files(cfg.get('exposure_ledger') or '',
                                           cfg.get('blind_from',
                                                   GP.DEFAULT_BLIND_FROM),
                                           synthetic=cfg.get('synthetic',
                                                             False))

    # ---- snapshot ----------------------------------------------------
    def snapshot(self):
        p = os.path.join(self.out_dir, 'godseye_snapshot.json')
        try:
            m = os.path.getmtime(p)
        except OSError:
            return None, dict(error='no snapshot at %s: run '
                                    'godseye_export.py first' % p)
        with self.lock:
            if self._snap[0] != m:
                try:
                    with open(p) as fh:
                        self._snap = (m, json.load(fh))
                except (OSError, ValueError) as exc:
                    return None, dict(error='snapshot unreadable: %s' % exc)
            return self._snap[1], None

    def status(self):
        p = os.path.join(self.out_dir, 'godseye_status.json')
        try:
            with open(p) as fh:
                return json.load(fh)
        except (OSError, ValueError) as exc:
            return dict(ok=None, error='no status file: %s' % exc)

    def served(self):
        """Snapshot + status + staleness, the one document the UI polls."""
        snap, err = self.snapshot()
        st = self.status()
        now = time.time()
        age = None if not snap else now - snap.get('generated_epoch', 0)
        stale = (snap is None) or (age is not None and age > STALE_AFTER_S) \
            or (st.get('ok') is False)
        return dict(server=SERVER_VERSION, served_utc=_iso(now),
                    snapshot=snap, snapshot_error=(err or {}).get('error'),
                    status=st, age_s=None if age is None else round(age, 1),
                    stale=stale,
                    stale_reason=((err or {}).get('error') if snap is None else
                                  ('last export failed: %s' % st.get('error')
                                   if st.get('ok') is False else
                                   ('snapshot is %d min old' % (age // 60)
                                    if stale else None))),
                    policy=self.policy.describe(),
                    replay_available=bool(self.cfg.get('capture_dir')) and
                    self.policy.ledger_days is not None)

    # ---- windows (exposed feature vectors) -----------------------------
    def windows(self):
        p = self.cfg.get('windows')
        if not p:
            return None, 'no windows file configured (pilot --windows-out)'
        try:
            m = os.path.getmtime(p)
        except OSError as exc:
            return None, 'windows file unreadable: %s' % exc
        with self.lock:
            if self._windows is None or self._windows[0] != m:
                with open(p) as fh:
                    doc = json.load(fh)
                idx = collections.defaultdict(list)
                for w in doc.get('windows', []):
                    idx[(str(w.get('session')), w.get('instrument'))].append(w)
                self._windows = (m, idx)
            return self._windows[1], None

    # ---- bundles -------------------------------------------------------
    def bundle(self, session, instrument, run, t_start, t_end):
        key = (session, instrument, run, round(t_start, 3), round(t_end, 3))
        with self.lock:
            if key in self._bundles:
                self._bundles.move_to_end(key)
                return self._bundles[key]
        import godseye_replay as GRP          # heavier import, on demand
        cap = self.cfg.get('capture_dir')
        if not cap:
            raise GP.PolicyError('replay unavailable: no capture folder '
                                 'configured on this computer')
        man = _find_manifest(cap, instrument, run)
        if man is None:
            raise GRP.ReplayError('no manifest for %s %s' % (instrument, run))
        if str(man.get('session')) != str(session):
            raise GP.PolicyError('run %s belongs to session %s, not %s'
                                 % (run, man.get('session'), session))
        # the policy again, on the run's OWN session label
        self.policy.require_inspectable([man.get('session')], 'replay')
        base = os.path.dirname(man['_path'])
        paths = {k: os.path.join(base, man[k]['file']) for k in
                 ('quotes', 'trades', 'depth', 'quality')
                 if isinstance(man.get(k), dict) and man[k].get('file')}
        if len(paths) < 4:
            raise GRP.ReplayError('run %s is missing a stream' % run)
        b = GRP.build_bundle(paths, float(t_start), float(t_end))
        b['session'] = str(session)
        b['instrument'] = instrument
        b['run'] = run
        with self.lock:
            self._bundles[key] = b
            while len(self._bundles) > BUNDLE_CACHE:
                self._bundles.popitem(last=False)
        return b


def _find_manifest(cap, instrument, run):
    for p in glob.glob(os.path.join(cap, '*_manifest*.json')):
        if p.endswith('.tmp'):
            continue
        try:
            with open(p) as fh:
                m = json.load(fh)
        except (OSError, ValueError):
            continue
        if m.get('instrument') == instrument and m.get('runId') == run:
            m['_path'] = p
            return m
    return None


def _iso(epoch):
    import datetime as _dt
    return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ')


class Handler(BaseHTTPRequestHandler):
    server_version = SERVER_VERSION
    state = None                          # set by serve()

    def log_message(self, fmt, *args):    # path only, never the query
        sys.stderr.write('%s %s\n' % (self.command,
                                      self.path.split('?', 1)[0]))

    # ---- helpers -----------------------------------------------------
    def _json(self, code, obj):
        body = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _static(self, rel):
        rel = rel.lstrip('/') or 'index.html'
        path = os.path.normpath(os.path.join(STATIC_DIR, rel))
        if not path.startswith(STATIC_DIR + os.sep) and path != STATIC_DIR:
            return self._json(404, dict(error='not found'))
        if not os.path.isfile(path):
            return self._json(404, dict(error='not found'))
        ext = os.path.splitext(path)[1].lower()
        with open(path, 'rb') as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header('Content-Type', _MIME.get(ext, 'application/octet-stream'))
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    # ---- routing -----------------------------------------------------
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        p = u.path
        st = self.state
        try:
            if p in ('/', '/index.html'):
                return self._static('index.html')
            if p.startswith('/static/'):
                return self._static(p[len('/static/'):])
            if p == '/api/snapshot':
                return self._json(200, st.served())
            if p == '/api/status':
                d = st.served()
                d.pop('snapshot', None)
                return self._json(200, d)
            if p == '/api/registry':
                return self._json(200, dict(
                    registry=GR.REGISTRY_VERSION, hypotheses=GR.HYPOTHESES,
                    resolved={h['id']: GR.resolve(h['id'])
                              for h in GR.HYPOTHESES},
                    demos=GR.DEMOS, demo_note=(
                        'SCRIPTED ILLUSTRATIONS: synthetic values chosen '
                        'so the final beat satisfies every frozen '
                        'condition (tests_godseye G11 runs the frozen '
                        'detector on them). Not market data; nothing here '
                        'is a result or an outcome'),
                    levels=GR.LEVELS, context=GR.CONTEXT,
                    not_in_this_version=GR.NOT_IN_THIS_VERSION,
                    discrepancies=GR.DISCREPANCIES))
            if p == '/api/replay/sessions':
                snap, err = st.snapshot()
                if snap is None:
                    return self._json(503, dict(error=err['error']))
                ex = snap.get('exposed', {}).get('sessions', {})
                ok = {s: v for s, v in ex.items() if st.policy.may_inspect(s)}
                return self._json(200, dict(
                    sessions=ok, policy=st.policy.describe(),
                    windows_file=snap.get('exposed', {}).get('windows_file')))
            if p == '/api/replay/windows':
                ses, inst = q.get('session'), q.get('instrument')
                st.policy.require_inspectable([ses], 'features')
                idx, err = st.windows()
                if idx is None:
                    return self._json(503, dict(error=err))
                ws = idx.get((str(ses), inst), [])
                return self._json(200, dict(session=ses, instrument=inst,
                                            windows=ws,
                                            explain={h['id']: GR.explain(
                                                h['id'], ws[0])
                                                for h in GR.WAVE_ONE}
                                            if ws else {}))
            if p == '/api/replay/explain':
                ses, inst = q.get('session'), q.get('instrument')
                st.policy.require_inspectable([ses], 'features')
                idx, err = st.windows()
                if idx is None:
                    return self._json(503, dict(error=err))
                te = float(q.get('t_end', 'nan'))
                w = next((w for w in idx.get((str(ses), inst), [])
                          if abs(float(w.get('t_end', 0)) - te) < 1e-6), None)
                if w is None:
                    return self._json(404, dict(error='no such window'))
                return self._json(200, dict(
                    window=w, explain={h['id']: GR.explain(h['id'], w)
                                       for h in GR.WAVE_ONE}))
            if p == '/api/replay/bundle':
                ses = q.get('session')
                st.policy.require_inspectable([ses], 'replay')
                b = st.bundle(ses, q.get('instrument'), q.get('run'),
                              float(q['t_start']), float(q['t_end']))
                return self._json(200, b)
            return self._json(404, dict(error='not found'))
        except GP.PolicyError as exc:
            return self._json(403, dict(error=str(exc), refused=True))
        except (KeyError, ValueError) as exc:
            return self._json(400, dict(error='bad request: %s' % exc))
        except Exception as exc:                        # noqa: BLE001
            return self._json(500, dict(error='%s: %s' % (type(exc).__name__,
                                                          exc)))


def load_config(path):
    with open(path) as fh:
        cfg = json.load(fh)
    base = os.path.dirname(os.path.abspath(path))
    for k in ('capture_dir', 'reports_dir', 'exposure_ledger', 'out_dir',
              'windows'):
        if cfg.get(k) and not os.path.isabs(cfg[k]):
            cfg[k] = os.path.normpath(os.path.join(base, cfg[k]))
    return cfg


def make_server(cfg, bind='127.0.0.1', port=8765):
    Handler.state = State(cfg)
    return ThreadingHTTPServer((bind, port), Handler)


def main(argv=None):
    p = argparse.ArgumentParser(description=SERVER_VERSION)
    p.add_argument('--config', required=True)
    p.add_argument('--port', type=int, default=None)
    p.add_argument('--bind', default=None)
    a = p.parse_args(argv)
    cfg = load_config(a.config)
    bind = a.bind or cfg.get('bind') or '127.0.0.1'
    port = a.port or int(cfg.get('port') or 8765)
    srv = make_server(cfg, bind, port)
    print('%s on http://%s:%d/  (snapshot dir: %s)'
          % (SERVER_VERSION, bind, port, cfg['out_dir']))
    print('read-only; Ctrl+C stops it; the recorder is not touched')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
