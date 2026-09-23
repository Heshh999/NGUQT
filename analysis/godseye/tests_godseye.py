#!/usr/bin/env python3
# MROF God's Eye View suite. Exercised on a small synthetic demonstration
# built by godseye_demo (labelled synthetic; zero fires on a sine-wave
# tape is expected) and on hand-built records. Synthetic fixtures verify
# CODE BEHAVIOUR only -- never predictive ability, never positive EV.
import glob
import hashlib
import json
import os
import random
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in ('.', '..', '../mrofyt', '../mrof', '../rvmr'):
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, _p)))

import godseye_demo as GD              # noqa: E402
import godseye_export as GE            # noqa: E402
import godseye_policy as GP            # noqa: E402
import godseye_registry as GR          # noqa: E402
import godseye_replay as GRP           # noqa: E402
import godseye_server as GS            # noqa: E402
import mrofyt_levels as LV             # noqa: E402
import mrofyt_pilot as PI              # noqa: E402
import mrofyt_runner as RN             # noqa: E402
import mrofyt_signals as SIG           # noqa: E402
import mrofyt_wave2 as W2              # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def tree_hash(d):
    return {os.path.basename(p): sha(p)
            for p in sorted(glob.glob(os.path.join(d, '*')))
            if os.path.isfile(p)}


WORK = tempfile.mkdtemp(prefix='godseye_')
REPO_LEDGER = os.path.join(HERE, '..', 'mrofyt', 'MROF_EXPOSED_PILOT_DEV_DAYS.json')
LOCK = os.path.join(HERE, '..', 'mrof', 'MROF_V1_STATE_C_AUTHORIZED.json')
repo_ledger_before = sha(REPO_LEDGER)

# ---------------------------------------------------------------------
# G1: the registry is the code
# ---------------------------------------------------------------------
t('G1: the registry names exactly the frozen active levels, and A6 / '
  'W2-A4-OPEN / z15 carry the runner\'s and wave two\'s own constants',
  [x['id'] for x in GR.LEVELS] == list(LV.ACTIVE_LEVEL_IDS) and
  tuple(GR.by_id('A6')['level_set']) == tuple(RN.OPEN_LEVELS) and
  GR.by_id('A6')['window_et'] == (9.5 * 3600, 9.75 * 3600) and
  tuple(GR.by_id('W2-A4-OPEN')['level_set']) == tuple(W2.OPEN_LEVELS_W2) and
  tuple(GR.by_id('W2-A4-OPEN')['window_et']) == tuple(W2.OPEN_WINDOW_ET) and
  GR.by_id('W2-A4r-z15')['threshold_change']['variant'] == W2.Z15 and
  GE._verify_registry() == [])

rng = random.Random(11)


def rf():
    c = rng.choice
    return dict(aggr_z=c([None, 0.5, 1.7, 2.0, 2.5]), aggr_dir=c([1, -1]),
                progress_ticks=c([None, 0, 1, 2]), opp_flip_z=c([None, .2, 1., 1.4]),
                returned_through_level=c([True, False]), sweep_reclaimed_5s=c([True, False]),
                replenish_z=c([None, 1.0, 1.5, 2.2]), approaches_60s=c([1, 2, 3]),
                retreat_ticks=c([None, 0, 1, 2]), resid_tail_5pct=c([None, True, False]),
                wall_z=c([None, 1.0, 2.0, 3.0]), exec_vs_displayed=c([None, 1.0, 1.5, 2.0]),
                replenish_ratio=c([None, .1, .25, .5]), cleared_held_5s=c([None, True, False]),
                persist_agree=c([None, 2, 3, 4]), post_clear_z=c([None, .5, 1., 1.5]),
                break_dir=c([1, -1]), trend_dir=c([None, 0, 1, -1]), adverse_z=c([None, 1., 2., 3.]),
                adverse_progress_ticks=c([None, 0, 1, 2]), trend_flip_z=c([None, .5, 1., 1.5]),
                in_0930_0945=c([True, False]), control_z=c([None, 1., 2., 3.]),
                clean_cross=c([None, True, False]), held_5s=c([None, True, False]),
                opp_replenish_z=c([None, 1., 1.5, 2.]), actions_distinguishable=c([True, False]),
                tgt_drop_frac=c([None, .5, .6, .7]), opp_drop_frac=c([None, .1, .2, .3]),
                delta_z=c([None, .5, 1., 1.5]), advance_ticks=c([None, 0, 1, 2]),
                vacuum_dir=c([1, -1]))


bad = 0
for _ in range(20000):
    f = rf()
    for hid in ('A1', 'A2', 'A3', 'A4', 'A5', 'A6'):
        if GR.explain(hid, f)['all_passed'] != (SIG.DETECTORS[hid](f) != 0):
            bad += 1
t('G1b: the registry\'s written conditions reproduce every frozen '
  'detector\'s verdict on 20,000 random feature vectors (A1-A6), so the '
  'evidence panel can never disagree with the code',
  bad == 0)

t('G1c: every discrepancy the build prompt asked about is recorded, with '
  'the code-verified reading, and A2/A5/A6 directions are quoted from '
  'the frozen functions',
  {d['item'] for d in GR.DISCREPANCIES} >= {'A2 direction', 'A5 direction',
                                             'A6 versus W2-A4-OPEN',
                                             'prior history: 5 versus 20',
                                             'A5 inputs that exist',
                                             'swing levels and Asia labels'} and
  GR.by_id('A2')['direction_sign'] == 'break_dir' and
  GR.by_id('A5')['direction_sign'] == 'trend_dir' and
  GR.by_id('A6')['direction_sign'] == 'break_dir' and
  GR.by_id('A4')['direction_sign'] == '-aggr_dir' and
  set(GR.by_id('A5')['not_wired']) == {'trend_dir', 'adverse_z',
                                        'adverse_progress_ticks',
                                        'trend_flip_z'})

# ---------------------------------------------------------------------
# G2: the policy fails closed
# ---------------------------------------------------------------------
lp = os.path.join(WORK, 'ledger.json')
json.dump(dict(exposed_days=[dict(session='20260901', label=GP.EXPOSURE_LABEL),
                             dict(session='20260921', label=GP.BLIND_LABEL)]),
          open(lp, 'w'))
pol = GP.Policy.from_files(lp)
cls = {s: pol.session_class(s) for s in ('20260901', '20260902', '20260921',
                                          '20260930', None)}
try:
    pol.require_inspectable(['20260901', '20260902'])
    mixed = None
except GP.PolicyError as exc:
    mixed = str(exc)
punk = GP.Policy.from_files(os.path.join(WORK, 'missing.json'))
try:
    punk.require_inspectable(['20260901'])
    unk_refused = False
except GP.PolicyError:
    unk_refused = True
t('G2: EXPOSED only when the ledger says so; a date before the hold-out '
  'that is not listed is PROTECTED; >= blind_from is BLIND; None is '
  'UNKNOWN; a mixed request is refused whole; an unreadable ledger makes '
  'everything UNKNOWN and refuses',
  cls == {'20260901': 'EXPOSED', '20260902': 'PROTECTED_UNLISTED',
          '20260921': 'BLIND', '20260930': 'BLIND', None: 'UNKNOWN'} and
  mixed and 'mixed' in mixed and unk_refused and
  punk.session_class('20260901') == 'UNKNOWN' and
  pol.permits('20260921', 'counts') and not pol.permits('20260921', 'events')
  and pol.permits('20260902', 'operational') and
  not pol.permits('20260902', 'replay') and
  not punk.permits('20260901', 'counts'))

t('G2b: the outcome-unlock file is absent and the policy only reads its '
  'state -- no code path in the dashboard names it for writing',
  not os.path.exists(LOCK) and
  GP.outcome_lock_state(os.path.join(HERE, '..', 'mrof'))['exists'] is False and
  all('MROF_V1_STATE_C_AUTHORIZED' not in open(os.path.join(HERE, f)).read()
      or f == 'godseye_policy.py'
      for f in ('godseye_export.py', 'godseye_server.py', 'godseye_replay.py',
                'godseye_demo.py', 'godseye_registry.py')))

# ---------------------------------------------------------------------
# G3: the synthetic demonstration, exported, is clean at the boundary
# ---------------------------------------------------------------------
DEMO = os.path.join(WORK, 'demo')
cfg = GD.build(DEMO, n_depth=6000, quiet=True)
cap_before = tree_hash(cfg['capture_dir'])
st = GE.write_snapshot(cfg)
snap = json.load(open(os.path.join(cfg['out_dir'], 'godseye_snapshot.json')))
demo_pol = GP.Policy.from_files(cfg['exposure_ledger'])
outside = {k: v for k, v in snap.items() if k != 'exposed'}
hits = GP.scan_for_event_level(outside)
t('G3: the export succeeds, is labelled synthetic, and carries NO '
  'event-level key anywhere outside its exposed section',
  st['ok'] and snap['synthetic'] and 'SYNTHETIC' in snap['synthetic_label']
  and hits == [] and st['duration_s'] < 60)

t('G3b: every session in the exposed section is EXPOSED in the demo\'s own '
  'ledger; blind and unlisted sessions appear in the timeline with '
  'operational facts only',
  all(demo_pol.may_inspect(s) for s in snap['exposed']['sessions']) and
  {s['session_class'] for s in snap['sessions']} >= {'EXPOSED', 'BLIND'} and
  all('direction' not in json.dumps(s) and '"fires"' not in json.dumps(s)
      for s in snap['sessions']))

pilot = json.load(open(os.path.join(cfg['reports_dir'], 'pilot.json')))
wave2 = json.load(open(os.path.join(cfg['reports_dir'], 'wave2.json')))
cp, cw = snap['counts']['pilot'], snap['counts']['wave2']
t('G3c: research counts are quoted from the released reports, not '
  'recomputed -- family totals equal the report\'s, per-session entries '
  'are integers only, and the source report is named with its time',
  cp['raw_fires_by_family'] == pilot['step6_frozen_signals']['by_family'] and
  cp['distinct_events_by_family'] ==
  pilot['step6_frozen_signals']['dedup']['distinct_events_by_family'] and
  all(cw['families'][f]['raw_fires'] == wave2['real']['families'][f]['raw_fires']
      for f in W2.FAMILIES) and
  all(isinstance(n, int) for fam in cp['distinct_events_by_family_and_session'].values()
      for n in fam.values()) and
  cp['source']['path'].endswith('pilot.json') and cp['source']['mtime_utc'])

t('G3d: no dashboard activity wrote into the capture folder, and the '
  'repository\'s exposure ledger is byte-identical (the demo has its own)',
  tree_hash(cfg['capture_dir']) == cap_before and
  sha(REPO_LEDGER) == repo_ledger_before and
  cfg['exposure_ledger'] != os.path.abspath(REPO_LEDGER))

fams = {f['id']: f for f in snap['hypotheses']['families']}
t('G3e: readiness statuses are distinct and reasoned: A5 is NOT_WIRED '
  '(four inputs None), the swing comparison is NOT_IMPLEMENTED, ARM-C is '
  'CONTROL, and every family carries at least one reason',
  fams['A5']['status'] == 'NOT_WIRED' and
  fams['CAUSAL_SWING comparison']['status'] == 'NOT_IMPLEMENTED' and
  fams['ARM-C']['status'] == 'CONTROL' and
  all(f.get('reasons') for f in fams.values()) and
  snap['hypotheses']['spec_mismatch'] == [])

# ---------------------------------------------------------------------
# G4: unreadable storage is UNAVAILABLE, never zero; stale is visible
# ---------------------------------------------------------------------
gone = dict(cfg, capture_dir=os.path.join(WORK, 'no_such_drive'),
            out_dir=os.path.join(WORK, 'out_gone'))
st4 = GE.write_snapshot(gone)
s4 = json.load(open(os.path.join(gone['out_dir'], 'godseye_snapshot.json')))
t('G4: a capture folder that cannot be read exports health UNAVAILABLE '
  'with the error, instruments UNAVAILABLE, and no coverage claim at all',
  st4['ok'] and s4['health']['status'] == 'UNAVAILABLE' and
  s4['health']['readable'] is False and 'error' in s4['health'] and
  s4['sessions'] == [] and 'instruments' not in s4['health'])

first_gen = snap['generated_utc']
time.sleep(1.1)
bad_cfg = dict(cfg, capture_dir=cfg['capture_dir'],
               out_dir=os.path.join(cfg['out_dir']))
bad_cfg['exposure_ledger'] = cfg['exposure_ledger']
bad_cfg['out_dir'] = cfg['capture_dir']          # refused: inside capture
st5 = GE.write_snapshot(dict(bad_cfg, out_dir=os.path.join(
    cfg['capture_dir'], 'x')))
t('G4b: the exporter refuses to write inside the capture folder, reports '
  'the failure in its status file, and leaves the capture untouched',
  st5['ok'] is False and 'must not be inside' in st5['error'] and
  tree_hash(cfg['capture_dir']) == cap_before)

# make the next export fail in place: the snapshot must survive and the
# server must call it stale with the reason
failing = dict(cfg, capture_dir=os.path.join(WORK, 'no_such_drive_2'))
os.makedirs(failing['capture_dir'])
GE.build_snapshot_orig = GE.build_snapshot


def _boom(cfg_, now=None):
    raise RuntimeError('simulated: drive vanished mid-export')


GE.build_snapshot = _boom
try:
    st6 = GE.write_snapshot(failing)
finally:
    GE.build_snapshot = GE.build_snapshot_orig
served = GS.State(cfg).served()
t('G4c: a failed export leaves the previous snapshot in place and the '
  'server marks it STALE with the current error and the last good time',
  st6['ok'] is False and 'simulated' in st6['error'] and
  json.load(open(os.path.join(cfg['out_dir'], 'godseye_snapshot.json')))[
      'generated_utc'] == first_gen and
  served['stale'] is True and 'simulated' in served['stale_reason'] and
  served['snapshot']['generated_utc'] == first_gen)
GE.write_snapshot(cfg)                             # restore a good status

# ---------------------------------------------------------------------
# G5: shared outages stay visible beside a perfect pair overlap
# ---------------------------------------------------------------------
def _iso(e):
    import datetime as _dt
    return _dt.datetime.fromtimestamp(e, _dt.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%S.0000000Z')


e0, e1 = GE.session_window_utc('20260915')
mk = lambda inst, a, b, rid: dict(instrument=inst, session='20260915',  # noqa: E731
                                  runId=rid, captureInstanceId='x-' + inst,
                                  contract='NQ DEC26', recorderBuild='1.2.2',
                                  closeReason='SESSION_ROLL', source='recorder',
                                  firstRecvUtc=_iso(a), lastRecvUtc=_iso(b),
                                  first_recv_epoch=a, last_recv_epoch=b)
cap5 = dict(manifest_runs=[mk('NQ', e0, e0 + 3600, 'a-R001'),
                           mk('NQ', e0 + 7200, e1, 'a-R002'),
                           mk('MNQ', e0, e0 + 3600, 'b-R001'),
                           mk('MNQ', e0 + 7200, e1, 'b-R002')],
            runs_without_manifest=[])
reports5 = {k: dict(ok=False, doc=None) for k in GE.REPORT_PATTERNS}
reports5['audit'] = dict(ok=True, doc=dict(runs=[], info=dict(
    overlaps={'20260915': dict(overlap_frac=1.0)})))
ses5 = GE.build_sessions(cap5, reports5, demo_pol, e1 + 10)[0]
t('G5: an hour missing in BOTH instruments is reported as a shared gap '
  'of that hour even though the pair overlap reads 1.000',
  ses5['pair_overlap_frac'] == 1.0 and
  abs(ses5['shared_gap_s'] - 3600) < 1 and
  abs(ses5['instruments']['NQ']['gap_s'] - 3600) < 1 and
  'cannot see' in ses5['pair_note'])

# ---------------------------------------------------------------------
# G6: missing code and insufficient history are different statuses
# ---------------------------------------------------------------------
def _fun(stage_counts, missing, passed=0, windows=100):
    return dict(windows=windows, first_failing_stage=stage_counts,
                missing_inputs=missing, passed=passed, fires_recorded=passed)


A1, A5, A6, A4 = (GR.by_id(x) for x in ('A1', 'A5', 'A6', 'A4'))
young = dict(baseline_sessions=dict(NQ=2, MNQ=2))
old = dict(baseline_sessions=dict(NQ=9, MNQ=9))
s_hist = GE._status_from_funnel(A1, _fun({'inputs_available': 100},
                                         {'aggr_z': 100}), young, {})[0]
s_amb = GE._status_from_funnel(A1, _fun({'inputs_available': 100},
                                        {'aggr_z': 100}), old, {})
s_exec = GE._status_from_funnel(A1, _fun({'inputs_available': 100},
                                         {'replenish_z': 100}), old, {})[0]
s_wired = GE._status_from_funnel(A5, _fun({'inputs_available': 100},
                                          {'trend_dir': 100}), old, {})[0]
s_gate = GE._status_from_funnel(A6, _fun({'in_0930_0945': 90,
                                          'control_z>=2.0': 10}, {}),
                                old, {})[0]
s_cond = GE._status_from_funnel(A4, _fun({'aggr_z>=2.0': 80,
                                          'response_failed': 20}, {}),
                                old, {})[0]
s_ready = GE._status_from_funnel(A4, _fun({'aggr_z>=2.0': 80}, {}, passed=3),
                                 old, {})[0]
t('G6: fewer than 5 baseline sessions -> INSUFFICIENT_PRIOR_HISTORY; an '
  'input the runner passes as None -> NOT_WIRED; replenishment undefined '
  'for want of an execution -> NO_QUALIFYING_OBSERVATIONS; outside the '
  'open window -> CONDITION_FALSE; inputs complete but a threshold failed '
  '-> CONDITION_FALSE; passed windows -> READY',
  s_hist == 'INSUFFICIENT_PRIOR_HISTORY' and s_wired == 'NOT_WIRED' and
  s_exec == 'NO_QUALIFYING_OBSERVATIONS' and s_gate == 'CONDITION_FALSE' and
  s_cond == 'CONDITION_FALSE' and s_ready == 'READY')
t('G6b: with >= 5 baseline sessions a z that is still None is NOT called '
  'prior history -- the report cannot say whether the bucket was short '
  'or the dispersion was zero, and the reason says so',
  s_amb[0] == 'INVALID_OR_MISSING_DATA' and
  'does not distinguish' in s_amb[1][0])

# ---------------------------------------------------------------------
# G7: session boundaries and daylight saving
# ---------------------------------------------------------------------
import datetime as _dt                                            # noqa: E402


def _utc(y, m, d, hh, mm=0):
    return _dt.datetime(y, m, d, hh, mm, tzinfo=_dt.timezone.utc).timestamp()


a, b = GE.session_window_utc('20260922')          # EDT: UTC-4
c, d = GE.session_window_utc('20261102')          # first Monday after DST ends (Nov 1 2026): EST, UTC-5
t('G7: a session\'s expected window is 18:00 ET the day before to 17:00 '
  'ET, and it follows daylight saving: 22:00Z-21:00Z in September, '
  '23:00Z-22:00Z in November',
  a == _utc(2026, 9, 21, 22) and b == _utc(2026, 9, 22, 21) and
  c == _utc(2026, 11, 1, 23) and d == _utc(2026, 11, 2, 22))
t('G7b: the market-hours rule: Saturday closed, Sunday opens 18:00 ET, '
  'Friday closes 17:00 ET, and the daily 17:00-18:00 ET halt is closed',
  not GE.market_open(_utc(2026, 9, 19, 15)) and          # Saturday
  not GE.market_open(_utc(2026, 9, 20, 21, 59)) and      # Sunday 17:59 EDT
  GE.market_open(_utc(2026, 9, 20, 22)) and              # Sunday 18:00 EDT
  GE.market_open(_utc(2026, 9, 25, 20, 59)) and          # Friday 16:59 EDT
  not GE.market_open(_utc(2026, 9, 25, 21)) and          # Friday 17:00 EDT
  not GE.market_open(_utc(2026, 9, 22, 21, 30)) and      # Tue 17:30 EDT halt
  GE.market_open(_utc(2026, 9, 22, 22)))                 # Tue 18:00 EDT
t('G7c: the timeline records every session with both the ET expectation '
  'and its UTC epochs, so a reader can check the conversion',
  all(len(s['expected_utc']) == 2 and len(s['expected_epoch']) == 2 and
      s['expected_epoch'][1] > s['expected_epoch'][0] for s in snap['sessions']))

# ---------------------------------------------------------------------
# G8: the server boundary, over real HTTP
# ---------------------------------------------------------------------
srv = GS.make_server(cfg, '127.0.0.1', 0)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def get(path):
    def body(resp):
        raw = resp.read().decode()
        try:
            return json.loads(raw)
        except ValueError:
            return dict(_text=raw)
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d%s' % (port, path),
                                    timeout=30) as r:
            return r.status, body(r)
    except urllib.error.HTTPError as e:
        return e.code, body(e)


code, doc = get('/api/snapshot')
exposed = sorted(snap['exposed']['sessions'])
blind = [s['session'] for s in snap['sessions'] if s['session_class'] == 'BLIND']
prot = [s['session'] for s in snap['sessions']
        if s['session_class'] == 'PROTECTED_UNLISTED']
c1, w1 = get('/api/replay/windows?session=%s&instrument=NQ' % exposed[0])
c2, w2 = get('/api/replay/windows?session=%s&instrument=NQ' % blind[0])
c3, w3 = get('/api/replay/windows?session=%s&instrument=NQ' % prot[0])
c4, w4 = get('/api/replay/windows?session=%s&instrument=NQ' % 'none')
t('G8: over HTTP the snapshot is served; windows of an EXPOSED session are '
  'returned; a BLIND session, an unlisted session and an unknown session '
  'are refused with 403 and a policy reason, never with data',
  code == 200 and doc['snapshot']['schema'] == GE.SNAPSHOT_SCHEMA and
  c1 == 200 and len(w1['windows']) > 0 and
  c2 == 403 and w2.get('refused') and 'windows' not in w2 and
  c3 == 403 and w3.get('refused') and c4 == 403 and w4.get('refused'))

win = w1['windows'][0]
q = 'session=%s&instrument=NQ&run=%s&t_start=%s&t_end=%s' % (
    exposed[0], win['run'], win['t_start'], win['t_end'])
cb, bundle = get('/api/replay/bundle?' + q)
qb = 'session=%s&instrument=NQ&run=%s&t_start=%s&t_end=%s' % (
    blind[0], win['run'], win['t_start'], win['t_end'])
cbb, bb = get('/api/replay/bundle?' + qb)
# a run from an exposed session requested under a blind label
runs_blind = [r for s in snap['sessions'] if s['session'] == blind[0]
              for r in s['instruments']['NQ']['runs']]
qc = 'session=%s&instrument=NQ&run=%s&t_start=%s&t_end=%s' % (
    exposed[0], runs_blind[0]['run_id'], win['t_start'], win['t_end'])
cbc, bc = get('/api/replay/bundle?' + qc)
t('G8b: a replay bundle for an exposed window is served with candles, '
  'BBO, tape and depth snapshots read in bounded seeks; the same request '
  'under a blind label is refused; a blind run smuggled under an exposed '
  'label is refused on the run\'s OWN session',
  cb == 200 and bundle['candles'] and bundle['depth_snapshots'] and
  isinstance(bundle['bbo'], list) and bundle['bytes_read'] < 8e6 and
  cbb == 403 and bb.get('refused') and cbc == 403 and bc.get('refused'))

ce, ex = get('/api/replay/explain?session=%s&instrument=NQ&t_end=%s'
             % (exposed[0], win['t_end']))
t('G8c: the evidence endpoint explains a window with the registry\'s '
  'conditions, each marked passed / failed / None, and its verdict '
  'agrees with the frozen detector on that very feature vector',
  ce == 200 and set(ex['explain']) == {'A1', 'A2', 'A3', 'A4', 'A5', 'A6'}
  and all(ex['explain'][k]['all_passed'] == (SIG.DETECTORS[k](ex['window'])
                                              != 0) for k in ex['explain']))

cs, _ = get('/static/../godseye_policy.py')
ci, idx = get('/')
t('G8d: static files are served from static/ only (traversal is 404) and '
  'the index page is served',
  cs == 404 and ci == 200 and 'God' in idx.get('_text', ''))

api_outside = {k: v for k, v in doc['snapshot'].items() if k != 'exposed'}
t('G8e: the document the browser receives carries no event-level key '
  'outside the exposed section either -- the export boundary survives '
  'serving',
  GP.scan_for_event_level(api_outside) == [] and
  all(demo_pol.may_inspect(s) for s in doc['snapshot']['exposed']['sessions']))
srv.shutdown()

# ---------------------------------------------------------------------
# G9: the replay reader is bounded and honest about depth
# ---------------------------------------------------------------------
man = GS._find_manifest(cfg['capture_dir'], 'NQ', win['run'])
base = os.path.dirname(man['_path'])
paths = {k: os.path.join(base, man[k]['file']) for k in
         ('quotes', 'trades', 'depth', 'quality')}
rows, info = GRP.read_rows(paths['depth'], 'depth', win['t_start'] - 60,
                           win['t_end'] + 60, max_rows=50)
first_t = json.load(open(man['_path']))['firstRecvUtc']
t0 = GRP.AD.iso_to_epoch(first_t)
early = GRP.build_bundle(paths, t0 + 0.5, t0 + 10.5, pre_s=0.6, post_s=1.0,
                         candle_context_s=5.0)
t('G9: the row cap truncates a read and says so; a window at the very '
  'start of a run shows a book with FEWER than ten known levels rather '
  'than ten invented ones',
  info['truncated'] and info['rows'] == 50 and
  any(len(s[1]) < 10 or len(s[2]) < 10 for s in early['depth_snapshots']) and
  'absent, not invented' in early['depth_note'])
off = GRP.find_offset(paths['trades'], 'trades', win['t_start'])
size = os.path.getsize(paths['trades'])
rows2, info2 = GRP.read_rows(paths['trades'], 'trades', win['t_start'],
                             win['t_end'])
t('G9b: the byte-offset search lands inside the file and the forward '
  'read returns only rows inside [t0, t1], reading far less than the file',
  0 < off <= size and all(win['t_start'] <= r['t_recv'] <= win['t_end']
                          for r in rows2) and
  info2['bytes_read'] < size / 2)

# ---------------------------------------------------------------------
# G10: the windows file the pilot writes for replay holds exposed
# sessions only
# ---------------------------------------------------------------------
wdoc = json.load(open(cfg['windows']))
t('G10: the pilot\'s windows file names its rule, lists only sessions '
  'below the blind, and every record carries the causal level snapshot',
  'EXPOSED' in wdoc['note'] and
  all(s < PI.BLIND_FROM for s in wdoc['sessions']) and
  all(isinstance(w.get('levels'), dict) for w in wdoc['windows'][:50]))

_ORDER_TOKENS = ('Submit' + 'Order', 'Enter' + 'Long', 'Enter' + 'Short',
                 'compute_' + 'outcomes(', 'simu' + 'late(',
                 'entry_' + 'fill(')
t('G10b: no dashboard module names an order API or the outcome stage '
  '(the tokens are assembled here so this file does not trip itself)',
  not any(any(tok in open(f).read() for tok in _ORDER_TOKENS)
          for f in glob.glob(os.path.join(HERE, 'godseye_*.py'))))

# ---------------------------------------------------------------------
# G11: the mechanism theatre's scripts are the frozen rules, not a story
# ---------------------------------------------------------------------
import random                                             # noqa: E402
import mrofyt_signals as _SIG                             # noqa: E402
import mrofyt_wave2 as _W2                                # noqa: E402


def _frozen(hid, f, sod=9.87 * 3600):
    """The frozen code's own verdict on a feature dict."""
    if hid in _SIG.DETECTORS:
        return _SIG.DETECTORS[hid](f)
    return {'W2-A1': _W2.w2_a1, 'W2-A4r': _W2.w2_a4r, 'ARM-C': _W2.w2_a4r,
            'W2-A4f': lambda g: _W2.w2_a4f(g)[0],
            'W2-A4-OPEN': lambda g: _W2.w2_a4_open(
                dict(g, level_id='CASH_OPEN_0930'),
                sod if g.get('in_0930_1030') else 10.75 * 3600),
            'W2-A4r-z15': _W2.w2_a4r_z15, 'W2-A4r-HC': _W2.w2_a4r_hc}[hid](f)


flow_demos = [d for d in GR.DEMOS if d.get('kind') != 'candles']
candle_demos = [d for d in GR.DEMOS if d.get('kind') == 'candles']
t('G11: every hypothesis has one scripted demo, and on each flow demo\'s '
  'final beat the FROZEN detector fires, in the direction the registry\'s '
  'rule names, while the registry\'s written conditions agree',
  {d['id'] for d in GR.DEMOS} == {h['id'] for h in GR.HYPOTHESES} and
  all(_frozen(d['id'], GR.demo_inputs(d)) != 0 and
      GR.explain(d['id'], GR.demo_inputs(d))['all_passed'] and
      _frozen(d['id'], GR.demo_inputs(d)) == (
          -GR.demo_inputs(d)[sign[1:]] if sign.startswith('-')
          else GR.demo_inputs(d)[sign])
      for d in flow_demos
      # the control keeps each family's own direction: W2-A4r's here
      for sign in [GR.resolve(d['id'])['direction_sign'] or '-aggr_dir']))


def _n_failing(hid, f):
    ex = GR.explain(hid, f)
    return (sum(1 for c in ex['gate'] + ex['conditions'] if c['passed'] is not True)
            + len(ex['inputs_missing']))


t('G11b: each counter-example changes one thing and does NOT fire in the '
  'frozen code; exactly one resolved clause fails (the control arm has no '
  'counter-example and is excluded)',
  all(_frozen(d['id'], GR.demo_inputs(d, counter=True)) == 0 and
      _n_failing(d['id'], GR.demo_inputs(d, counter=True)) == 1
      for d in flow_demos if d['id'] != 'ARM-C') and
  GR.demo_inputs(next(d for d in GR.DEMOS if d['id'] == 'ARM-C'),
                 counter=True) == GR.demo_inputs(
      next(d for d in GR.DEMOS if d['id'] == 'ARM-C')))


def _arm(d, bars):
    if d['id'] == 'ARM-B1':
        return _W2.arm_b1(bars[0], d['level_px'], d['ad'])
    return _W2.arm_b2(bars[0], bars[1], d['level_px'], d['ad'])


t('G11c: the candle arms\' bars fire -ad in the FROZEN arm functions and '
  'the counter-example bars do not',
  len(candle_demos) == 2 and
  all(_arm(d, d['bars']) == -d['ad'] and _arm(d, d['counter']['bars']) == 0
      for d in candle_demos))

# resolve(): a derived family's resolved conditions are its wave-two
# function, on random inputs including None
rng = random.Random(11)


def _rand_vec():
    pick = lambda *xs: rng.choice(xs)                    # noqa: E731
    return dict(aggr_z=pick(None, rng.uniform(0, 4)),
                aggr_z_hc=pick(None, rng.uniform(0, 4)),
                progress_ticks=pick(None, 0, 1, 2, 3),
                resid_tail_5pct=pick(None, True, False),
                returned_through_level=pick(None, True, False),
                sweep_reclaimed_5s=pick(None, True, False),
                opp_flip_z=pick(None, rng.uniform(0, 3)),
                repl10_z=pick(None, rng.uniform(0, 3)),
                replenish_z=pick(None, rng.uniform(0, 3)),
                approaches_60s=pick(None, 1, 2, 3),
                retreat_ticks=pick(None, 0, 1, 2),
                aggr_dir=pick(1, -1), in_0930_1030=pick(True, False))


vecs = [_rand_vec() for _ in range(6000)]
t('G11d: resolve() makes the registry judge each wave-two family exactly '
  'as mrofyt_wave2 does -- on 6,000 random inputs the resolved conditions '
  'and the frozen function agree for W2-A1, W2-A4r, W2-A4f, W2-A4-OPEN, '
  'W2-A4r-z15 and W2-A4r-HC (input swapped, forced None, required, gated, '
  'threshold changed)',
  all(GR.explain(hid, f)['all_passed'] == (_frozen(hid, f) != 0)
      for hid in ('W2-A1', 'W2-A4r', 'W2-A4f', 'W2-A4-OPEN', 'W2-A4r-z15',
                  'W2-A4r-HC')
      for f in vecs) and
  GR.resolve('W2-A4r-z15')['conditions'][0]['value'] == 1.5 and
  GR.resolve('W2-A4r')['forced_none'] == ['resid_tail_5pct'] and
  'resid_tail_5pct' in GR.resolve('W2-A4f')['required_inputs'] and
  GR.resolve('W2-A4r-HC')['required_inputs'][0] == 'aggr_z_hc')

# ---------------------------------------------------------------------
# G12: where the study stands -- complete sessions, runway, the clock
# ---------------------------------------------------------------------
_good = dict(session='20260910', expected_clipped_to_now=False, shared_gap_s=0.0,
             instruments={i: dict(covered_frac=0.99, runs=[dict(run_id='r', audit=dict(ok=True))])
                          for i in ('NQ', 'MNQ')})
_short = json.loads(json.dumps(_good)); _short['instruments']['MNQ']['covered_frac'] = 0.90
_gap = json.loads(json.dumps(_good)); _gap['shared_gap_s'] = 900.0
_open = json.loads(json.dumps(_good)); _open['instruments']['NQ']['runs'].append(
    dict(run_id='o', audit=dict(ok=None, note='no manifest: not auditable')))
_live = json.loads(json.dumps(_good)); _live['expected_clipped_to_now'] = True
t('G12: a session is complete only when its window has passed, both '
  'instruments cover >= 95%, no shared gap over 5 min, and every run passed '
  'the audit; each failing reason is named',
  GE.session_completeness(_good) == (True, 'complete') and
  not GE.session_completeness(_short)[0] and 'MNQ covers 90.0%' in GE.session_completeness(_short)[1] and
  not GE.session_completeness(_gap)[0] and '15 min missing in both' in GE.session_completeness(_gap)[1] and
  not GE.session_completeness(_open)[0] and 'not auditable' in GE.session_completeness(_open)[1] and
  GE.session_completeness(_live) == (False, 'session still in progress'))

prog = snap['progress']
t('G12b: the progress section of the demo snapshot counts sessions by that '
  'rule, carries the runbook milestones (20, 60) and the registration\'s '
  'checkpoint (2026-12-01, 30 NQ events, hard kill 200), lists every wave-one '
  'and wave-two family with an integer count, and projects a count only',
  prog['sessions_seen'] == len(snap['sessions']) and
  prog['sessions_complete'] == sum(1 for s in snap['sessions'] if GE.session_completeness(s)[0]) and
  [m['sessions'] for m in prog['milestones']] == [20, 60] and
  prog['checkpoint']['date'] == '20261201' and prog['family_min_events'] == 30 and
  prog['hard_kill_events'] == 200 and
  set(prog['nq_events_by_family']) >= {'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'W2-A1', 'W2-A4r'} and
  all(isinstance(v, int) for v in prog['nq_events_by_family'].values()) and
  all(isinstance(v, int) for v in prog['projected_by_checkpoint'].values()) and
  GP.scan_for_event_level(prog) == [])

sat_noon = GE.et_local_to_utc('20260926', 12)             # a Saturday
nxt, what = GE.market_next_change(sat_noon)
wed = GE.et_local_to_utc('20260923', 10)
nxt2, what2 = GE.market_next_change(wed)
t('G12c: the clock -- from Saturday noon ET the next change is the Sunday '
  '18:00 ET open; from Wednesday 10:00 ET it is the 17:00 ET halt; trading '
  'days to the checkpoint count weekdays only',
  what == 'opens' and nxt == GE.et_local_to_utc('20260927', 18) and
  what2 == 'closes' and nxt2 == GE.et_local_to_utc('20260923', 17) and
  GE.trading_days_between('20260925', '20260929') == 1 and     # Fri -> Mon
  GE.trading_days_between('20261127', '20261201') == 1)

disk = snap['health']['disk']
t('G12d: disk runway is the free space over the median finalized bytes per '
  'session-day, measured on sessions where both instruments closed a run, '
  'and says so',
  disk['sessions_measured'] > 0 and disk['bytes_per_session_day'] > 0 and
  abs(disk['runway_session_days'] - disk['free_bytes'] / disk['bytes_per_session_day']) < 0.1 and
  'median' in disk['runway_note'])

_recon = json.loads(json.dumps(_good))
_recon['instruments']['NQ']['runs'] = [dict(
    run_id='rr', audit=dict(ok=False, failure_codes=[
        'RECONSTRUCTED_RUN_NOT_SELF_VERIFYING']))]
_recon_bad = json.loads(json.dumps(_recon))
_recon_bad['instruments']['NQ']['runs'][0]['audit']['failure_codes'].append(
    'INSTANCE_SEQ_GAP')
t('G12e: after a weekend repair a session whose ONLY audit flag is '
  'RECONSTRUCTED_RUN_NOT_SELF_VERIFYING is complete and says it relies on '
  'a reconstructed manifest; any other flag beside it still makes the '
  'session incomplete, and the flag is named',
  GE.session_completeness(_recon) ==
  (True, 'complete, relying on 1 reconstructed manifest(s)') and
  not GE.session_completeness(_recon_bad)[0] and
  'INSTANCE_SEQ_GAP' in GE.session_completeness(_recon_bad)[1])

# ---------------------------------------------------------------------
# G13: replay windows are split once per pilot run; neither a routine
# export nor the server holds the whole file
# ---------------------------------------------------------------------
wf_size = os.path.getsize(cfg['windows'])
ix_path = os.path.join(cfg['out_dir'], GE.WINDOWS_INDEX_NAME)
st13 = GE.write_snapshot(cfg)                       # a routine export
s13 = json.load(open(os.path.join(cfg['out_dir'], 'godseye_snapshot.json')))
ix13 = json.load(open(ix_path))
wdoc13 = json.load(open(cfg['windows']))
inspectable13 = [w for w in wdoc13['windows']
                 if demo_pol.may_inspect(str(w['session']))]
pieces_ok = True
n_in_pieces = 0
for sh in ix13['shards']:
    p = json.load(open(os.path.join(cfg['out_dir'], ix13['dir'], sh['file'])))
    n_in_pieces += len(p['windows'])
    pieces_ok &= demo_pol.may_inspect(sh['session']) and all(
        str(w['session']) == sh['session'] and w['instrument'] == sh['instrument']
        for w in p['windows'])
t('G13: the first export split the windows file into one piece per '
  '(session, instrument) of inspectable sessions, each holding only its '
  'own windows and together all of them; a routine export reuses the '
  'split and does not read the windows file again',
  s13['exposed']['windows_file']['index'] == 'cached' and pieces_ok and
  n_in_pieces == len(inspectable13) and len(ix13['shards']) >= 2 and
  st['bytes_read'] - st13['bytes_read'] > 0.9 * wf_size)

old_dir13 = ix13['dir']
_t13 = os.path.getmtime(cfg['windows']) + 5
os.utime(cfg['windows'], (_t13, _t13))              # a new pilot run
GE.write_snapshot(cfg)
ix13b = json.load(open(ix_path))
_l13 = os.path.getmtime(cfg['exposure_ledger']) + 5
os.utime(cfg['exposure_ledger'], (_l13, _l13))      # the ledger moved on
GE.write_snapshot(cfg)
ix13c = json.load(open(ix_path))
t('G13a: a changed windows file, or a changed exposure ledger, rebuilds '
  'the split into a fresh directory and removes the old one',
  ix13b['dir'] != old_dir13 and ix13c['dir'] != ix13b['dir'] and
  not os.path.exists(os.path.join(cfg['out_dir'], old_dir13)) and
  not os.path.exists(os.path.join(cfg['out_dir'], ix13b['dir'])) and
  os.path.isdir(os.path.join(cfg['out_dir'], ix13c['dir'])))

stt = GS.State(dict(cfg))
pol_a = stt.policy
pairs = [(sh['session'], sh['instrument']) for sh in ix13c['shards']]
got = [stt.windows_for(s, i) for s, i in pairs]
_l13b = os.path.getmtime(cfg['exposure_ledger']) + 5
os.utime(cfg['exposure_ledger'], (_l13b, _l13b))
pol_b = stt.policy
t('G13b: the server reads one piece per (session, instrument), holds at '
  'most %d, returns nothing for a session with no piece, and re-reads the '
  'exposure ledger when it changes (no restart needed after a pilot run; '
  'still fail-closed)' % GS.SHARD_CACHE,
  all(err is None and ws and all(w['instrument'] == i for w in ws)
      for (ws, err), (_, i) in zip(got, pairs)) and
  len(stt._shards) <= GS.SHARD_CACHE < len(pairs) and
  stt.windows_for('20260921', 'NQ') == ([], None) and
  pol_b is not pol_a and not pol_b.may_inspect(prot[0]) and
  pol_b.may_inspect(exposed[0]))

_bat = open(os.path.join(HERE, 'launch_godseye.bat')).read()
t('G13c: the Windows launcher lets the server open the browser once it is '
  'listening, instead of racing it',
  '--open' in _bat and 'start ""' not in _bat and
  'webbrowser.open' in open(os.path.join(HERE, 'godseye_server.py')).read())

# the refresher: one export, run as a SEPARATE process by the server
_cfgp = os.path.join(DEMO, 'godseye.config.json')
_snap_p = os.path.join(cfg['out_dir'], 'godseye_snapshot.json')
_before_gen = json.load(open(_snap_p))['generated_epoch']
time.sleep(1.1)
_rc = GS.refresh_once(_cfgp)
_after = json.load(open(_snap_p))
_stat = json.load(open(os.path.join(cfg['out_dir'], 'godseye_status.json')))
t('G13d: while the dashboard is open the server keeps it fresh -- one '
  'export per tick, in a separate process (the launcher asks for every '
  '300 s), so the snapshot never silently goes stale during market hours',
  _rc == 0 and _stat['ok'] and _after['generated_epoch'] > _before_gen and
  '--refresh 300' in _bat and
  '--refresh 300' in open(os.path.join(HERE, 'pinokio', 'start.js')).read())

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
