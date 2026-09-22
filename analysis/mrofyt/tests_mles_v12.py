#!/usr/bin/env python3
# MLES-CAPTURE-1.2 suite: compiles the recorder with mcs (NT8 stubs),
# RUNS the real lifecycle harness with mono (writer/rotation/
# concurrency/shutdown actually exercised), audits its genuine output,
# then adds adversarial fixtures and package/doc proofs.
# Synthetic events verify CODE BEHAVIOR only, never market evidence.
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-66s %s' % (name, 'PASS' if cond else 'FAIL'))


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


# ---- lineage immutability (33 pinned hashes) ------------------------
PINNED = {}
for rel, want in [
    ('analysis/mrofyt/MROF_YT_OF01_WAVE_FREEZE.md',
     '881d6df8e9acb8fb5c597e55cfc8646f0a9b4f0ceab35604697051299d18ae48'),
    ('analysis/mrofyt/mrofyt_levels.py',
     '3c094d0280a7571aa1e7aed5fc59fa432722759bc8131d37115ee08bd03bc702'),
    ('analysis/mrofyt/mrofyt_signals.py',
     '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1'),
    ('analysis/mrofyt/tests_mrofyt.py',
     'c1ce10249dff41f437c6a21b629305b8bc4ac0453d0087475dfb2ea6dfa10e34'),
    ('analysis/mrofyt/MROF_YT_OF01_1_SUCCESSOR_FREEZE.md',
     '69d1dfb228681cf4097fc8f3cc800a3ce941d5edfef9bf915cd1534f8d2102dc'),
    ('analysis/mrofyt/mrofyt_h1zones.py',
     '9ee941e28f6f12b4a1d1c9a340f37990faa9f7c10a736d94c9437513922b8186'),
    ('analysis/mrofyt/mrofyt_wall_engine.py',
     'a8ccc3dd9a14de98bf6670026933db5153fd65155d0502bc776381aced332077'),
    ('analysis/mrofyt/tests_mrofyt_v01_1.py',
     '30e858e87d7fa81fc2c5ca1466e5f3afc2d14ef3cef6a1bbda4fb41eb467e776'),
    ('analysis/mrofyt/MROF_YT_OF01_2_SUCCESSOR_FREEZE.md',
     '77a58288791e6f861da2abc3dc736352aae01ea964c434f895d3bf2baf9cb639'),
    ('analysis/mrofyt/mrofyt_coordinator.py',
     '2db5524a1a8e4877931c2ad5b578c384d76808661a9994e2d15b33a11a4a66e8'),
    ('analysis/mrofyt/tests_mrofyt_v01_2.py',
     'ea3770f5e0772d2f46a35f55c3c89d08c5b6ce831bd0c6aaaaa549c45bdb8560'),
    ('analysis/mrofyt/RECORDER_DEPLOYMENT.md',
     'cb9d3fd0d1329dda1e0f8b39974995b8dfa10254d5170c16e7c1aefb948a5a30'),
    ('analysis/mrofyt/DATA_HANDOFF.md',
     '2d7a9400ee0823bedad0183d633900f691dfb8819f4d140b0ac0cbf2ff0652b2'),
    ('analysis/mrofyt/MROF_YT_OF01_3_SUCCESSOR_FREEZE.md',
     'a7af6b33f3ab3d5e73c6b4fd5146a18180f81ede4e615ed15fb4b2b28b13bf26'),
    ('analysis/mrofyt/mrofyt_coordinator_v013.py',
     'c0fd9f04d4c17b78722e74bd48f1dd4f57a521993907818fea0d65e75941d4ef'),
    ('analysis/mrofyt/tests_mrofyt_v01_3.py',
     '788248f531afc7e56ad793fb9a9a8828cdc180d605987c7ca36ab1104a18f971'),
    ('analysis/mrofyt/RECORDER_DEPLOYMENT_v01_3.md',
     'c5b0a9023631a5f1cc21fddc868bbbc95d9ec42dd825f08b34639bfa761293f4'),
    ('analysis/mrofyt/DATA_HANDOFF_v01_3.md',
     '71bcf2f6b23aae830bbaf9e84dce7161596921342f2788c0eb8b46c613376f8d'),
    ('analysis/mrofyt/MROF_YT_OF01_FINAL_SOURCE_PROMPT.md',
     '74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b'),
    ('analysis/mrofyt/MROF_YT_OF01_4_SUCCESSOR_FREEZE.md',
     'cfc27554cf1a889adde8f9be6f924d32d6902889db23eddd1c8fe9a8d765d020'),
    ('analysis/mrofyt/mrofyt_engine_v014.py',
     '8f80458add811d1799d31f061b91c585755c102f32854ce58f77678195b81a2d'),
    ('analysis/mrofyt/tests_mrofyt_v01_4.py',
     'd71e919549e8537d10e42cbc492206bf3a1ee4f8602e703204a27c14f4ba11c0'),
    ('analysis/mrofyt/REVIEW_PACKAGE_MANIFEST.md',
     'd3b4ad26b97ca20a3ccbdd93260dfbb26396ba25d14aeb5eb3b169e5ca233df1'),
    ('src/MlesV1CaptureHost.cs',
     'dab3abec22e16255cd27d198200125c5cd6a44192e7ff07d53ce798c755dd63d'),
    ('src/MlesV11CaptureHost.cs',
     '17a8c347d39e7187f81d7ca1fd6c7161440a8d1bfdc49823f23d1553c419815e'),
    ('analysis/mrofyt/mrofyt_engine_v015.py',
     'e3da36cd63a18a22935124e852ce8f8b785e96df136d98944f7e88654b1c6847'),
    ('analysis/mrofyt/tests_mrofyt_v01_5.py',
     '2f4c26df78246d739cb8bd3d1efec2cf283c2f7777b0710e37eff33f4c8bdebb'),
    ('analysis/mrofyt/mles_v11_adapter.py',
     '4ce2f94200334dc4597f7c2d79995158b8954e3d523e626dba5657855e53b8e1'),
    ('analysis/mrofyt/mles_v11_audit.py',
     'a4aed25eedc161e5c31db4b2144c9393408cdedc4d515229a5d9b2afc5efcbb9'),
    ('analysis/mrofyt/tests_mles_v11.py',
     '89cb51f4f18d45c1e2c7b1f2a449f763d04b08e5703907f1e5d002f177b78330'),
    ('analysis/mrofyt/MLES_CAPTURE_V11_FREEZE.md',
     '56d15e7518b339e0197c1e3222cfffea3c4b2b62ad170add4c0113149c67f5bb'),
    ('analysis/mrofyt/MROF_YT_OF01_5_SUCCESSOR_FREEZE.md',
     'b753a09cc077267a935df37f9b531f2179d920b8f76dc6ee5788628c264f7194'),
    ('analysis/mrofyt/REVIEW_PACKAGE_MANIFEST_v01_5.md',
     '7200844f334e272d75c6167cbcb9be20a0c7affed1bc4750cdeb9f551a035ba9'),
]:
    PINNED[rel] = want
t('lineage f99c521..97d2bc1 immutable (%d pinned hashes)' % len(PINNED),
  all(sha(os.path.join(ROOT, rel)) == w for rel, w in PINNED.items()))

import mles_v12_adapter as AD    # noqa: E402
import mles_v12_audit as AU      # noqa: E402
import mles_v12_synth as SY      # noqa: E402

# ---- compile the recorder + harness with mcs (stub syntax proof) ----
WORK = tempfile.mkdtemp(prefix='mles12t_', dir='/tmp')
EXE = os.path.join(WORK, 'harness.exe')
cp = subprocess.run(['mcs', '-out:' + EXE,
                     os.path.join(HERE, 'nt8_stubs_v12.cs'),
                     os.path.join(ROOT, 'src', 'MlesV12CaptureHost.cs'),
                     os.path.join(HERE, 'mles_v12_harness.cs')],
                    capture_output=True, text=True)
t('C# stub compile of v1.2 recorder + harness (mcs exit 0)',
  cp.returncode == 0)

# ---- run the REAL lifecycle harness ---------------------------------
H = os.path.join(WORK, 'out')
os.makedirs(H)
run = subprocess.run(['mono', EXE, H], capture_output=True, text=True,
                     timeout=300)
lines = dict()
for ln in run.stdout.splitlines():
    if ln.startswith('HARNESS '):
        parts = ln.split()
        lines[parts[1]] = dict(p.split('=', 1) for p in parts[2:])
t('lifecycle harness ran to completion (mono exit 0, done ok=1)',
  run.returncode == 0 and lines.get('done', {}).get('ok') == '1')


def runs_of(sub):
    return [AU.audit_run(m)
            for m in AU.discover_manifests(os.path.join(H, sub))]


rolls = runs_of('rolls')
sessions = sorted(r['info']['session'] for r in rolls)
# 1 + 2: consecutive sessions and three consecutive rolls
t('T1: two consecutive sessions record successfully (audited clean)',
  {'20260901', '20260902'} <= set(sessions) and
  all(r['ok'] for r in rolls[:2]))
t('T2: THREE consecutive session rolls preserve recording (4 runs, '
  'all clean)', len(rolls) == 4 and
  sessions == ['20260901', '20260902', '20260903', '20260904'] and
  all(r['ok'] for r in rolls))
# 6: writer stays alive after rotation (the v1.1 defect)
t('T6: writer stays ALIVE after every rotation - post-roll runs all '
  'have market rows',
  all(r['manifest']['quotes']['rows'] > 0 and
      r['manifest']['trades']['rows'] > 0 for r in rolls[1:]))
# 4: counters reset per run
t('T4: per-run counters/sequences reset (every run starts each '
  'stream at seq 1)',
  all(r['manifest']['firstQuoteSeq'] == 1 and
      r['manifest']['firstTradeSeq'] == 1 and
      r['manifest']['firstDepthSeq'] == 1 and
      r['manifest']['firstQualitySeq'] == 1 for r in rolls))
# 5: manifests match only their own files
q_hashes = [r['manifest']['quotes']['sha256'] for r in rolls]
t('T5: every manifest matches exactly its own files (audits clean, '
  'all file hashes distinct)',
  all(r['ok'] for r in rolls) and len(set(q_hashes)) == 4)

croll = runs_of('croll')
t('T3: contract roll isolates both contracts (two clean runs, one '
  'per contract)',
  len(croll) == 2 and all(r['ok'] for r in croll) and
  sorted(r['info']['contract'] for r in croll) ==
  ['NQ 03-27', 'NQ 12-26'])

conc = runs_of('conc')
ci = conc[0]['info']
t('T7: concurrent randomized producers preserve assignment order - '
  'clean audit, gapless 1..N union',
  len(conc) == 1 and conc[0]['ok'] and ci['seq_first'] == 1 and
  ci['seq_count'] == ci['seq_last'] and not ci['seq_holes'])
mkt_rows = sum(conc[0]['manifest'][s]['rows']
               for s in ('quotes', 'trades', 'depth'))
t('T7b: all 2400 produced + 14 preamble market events written',
  mkt_rows == 2414)

# 8: callbacks perform no hashing/joining/finalization
src = open(os.path.join(ROOT, 'src', 'MlesV12CaptureHost.cs')).read()


def body(name):
    i = src.index(name)
    j = src.index('{', i)
    depth, k = 0, j
    while True:
        if src[k] == '{':
            depth += 1
        elif src[k] == '}':
            depth -= 1
            if depth == 0:
                break
        k += 1
    return src[j:k]


cb_bodies = ''.join(body(n) for n in (
    'private void Publish', 'public void OnQuote',
    'public void OnTrade', 'public void OnDepth',
    'public void OnConnection'))
t('T8: no callback performs hashing, joining, moving, flushing or '
  'finalization',
  not any(tok in cb_bodies for tok in
          ('Sha256', 'Join', 'File.Move', 'Flush', 'CloseRun',
           'Finalize', 'Manifest')))

bigq = runs_of('bigq')
t('T9: large queued rotation loses no events (6004 trades across '
  'both runs, clean)',
  len(bigq) == 2 and all(r['ok'] for r in bigq) and
  sum(r['manifest']['trades']['rows'] for r in bigq) == 6004)

t('T10: termination before the first event leaves no files and no run',
  lines['noevent'] == dict(files='0', runs='0'))

worker_body = body('private void WorkerLoop')
shutdown_body = body('public void Shutdown')
t('T11: shutdown uses ONE queue consumer (single Dequeue site, in '
  'the worker; Shutdown only joins)',
  src.count('queue.Dequeue()') == 1 and
  'queue.Dequeue()' in worker_body and
  'Dequeue' not in shutdown_body and 'Join()' in shutdown_body)

restart = runs_of('restart')
cids = {r['info']['capture_instance_id'] for r in restart}
t('T12: restart creates a NEW capture instance and run (distinct '
  'ids, both clean, no collisions)',
  lines['restart']['distinct'] == '1' and len(restart) == 2 and
  len(cids) == 2 and all(r['ok'] for r in restart) and
  len({r['info']['run_id'] for r in restart}) == 2)

disco = runs_of('disco')[0]
man = disco['manifest']
t('T13: disconnect invalidates the book (DISCONNECT logged; '
  'suppressed intervals flagged; bookResets not zero)',
  disco['ok'] and man['bookResets'] == 1 and
  disco['info']['suppressed_rows'] == 15 and
  any(e['stream'] == 'QUALITY' and e['kind'] == 'DISCONNECT'
      for e in disco['events']))
t('T14: reconnect requires COMPLETE resynchronization (segId 2, a '
  'resync marker at BOTH the disconnect and the reconnect, two '
  'BOOK_READY)',
  man['connectionSegments'] == 2 and man['reconnects'] == 1 and
  disco['info']['book_resync_starts'] == 3 and
  disco['info']['book_ready'] == 2)
# The defect this pins: on disconnect the recorder cleared BookReady but
# left the gate maxima (MaxBidLvl/MaxAskLvl) at full depth, and those
# never decrease -- so the next depth row re-satisfied the gate and
# re-emitted BOOK_READY with no resync and no rebuild. The research
# runner treats BOOK_READY as permission to re-arm, so it would evaluate
# decision windows against a book the recorder had just invalidated. It
# went unseen because the harness sent only trades inside the gap; it
# now sends a depth row there (harness line ~193).
_dq = [e for e in disco['events'] if e['stream'] == 'QUALITY']
_kinds = [e['kind'] for e in _dq]
_i_dis = _kinds.index('DISCONNECT')
_i_rec = _kinds.index('RECONNECT')
t('T31: a depth row inside the disconnect gap produces NO BOOK_READY, '
  'and the disconnect emits its own BOOK_RESYNC_START so every ready '
  'stays preceded by a resync',
  'BOOK_READY' not in _kinds[_i_dis:_i_rec] and
  _kinds[_i_dis + 1] == 'BOOK_RESYNC_START' and
  disco['info']['book_ready'] <= disco['info']['book_resync_starts'] and
  disco['ok'])
# CONN control events must not consume published seqs: the instance
# union stays gapless and every file stays monotone even with
# disconnect/reconnect traffic; the occurrence instant survives in the
# CONN_STATUS detail. (Regression: v1.2 draft leaked seqs here.)
_dc = AU.audit_capture(os.path.join(H, 'disco'))
_dcodes = {c for c, _ in _dc['failures']}
t('T14b: disco capture union gapless + monotone (no INSTANCE_SEQ_GAP/'
  'RUN_AUDIT_FAILED); CONN_STATUS keeps occurrence stamps',
  'INSTANCE_SEQ_GAP' not in _dcodes and
  'RUN_AUDIT_FAILED' not in _dcodes and
  all('occurredUtc=' in e['detail'] and 'occurredMono=' in e['detail']
      for e in disco['events']
      if e['stream'] == 'QUALITY' and e['kind'] == 'CONN_STATUS') and
  sum(1 for e in disco['events']
      if e['stream'] == 'QUALITY' and e['kind'] == 'CONN_STATUS') == 2)

pair = AU.audit_capture(os.path.join(H, 'pair'))
ov = list(pair['info']['overlaps'].values())[0]
t('pair: NQ+MNQ same session pass with reported overlap >= 50%',
  pair['ok'] and ov['overlap_frac'] >= 0.5)
t('T15: NQ and MNQ from different sessions FAIL',
  'NQ_MNQ_SESSION_MISMATCH' in
  {c for c, _ in AU.audit_capture(os.path.join(H, 'pairbad'))['failures']})
t('T16: NQ/MNQ insufficient window overlap FAILS',
  'NQ_MNQ_INSUFFICIENT_OVERLAP' in
  {c for c, _ in AU.audit_capture(os.path.join(H, 'pairlow'))['failures']})

# 17/18/19/20: adversarial fixtures on a COPY of real recorder output
FIX = os.path.join(WORK, 'fix17')
shutil.copytree(os.path.join(H, 'rolls'), FIX)
m0 = AU.discover_manifests(FIX)[0]
j = json.load(open(m0))
j['firstEventSeq'] += 7
json.dump(j, open(m0, 'w'))
t('T17: falsified manifest sequence boundaries FAIL',
  'FIRST_EVENT_SEQ_MISMATCH' in
  {c for c, _ in AU.audit_run(m0)['failures']})
FIX2 = os.path.join(WORK, 'fix18')
shutil.copytree(os.path.join(H, 'disco'), FIX2)
m1 = AU.discover_manifests(FIX2)[0]
j = json.load(open(m1))
j['connectionSegments'] = 9
j['lastSegId'] = 9
json.dump(j, open(m1, 'w'))
t('T18: falsified segment counts FAIL',
  'SEG_COUNT_MISMATCH' in {c for c, _ in AU.audit_run(m1)['failures']})
FIX3 = os.path.join(WORK, 'fix19')
shutil.copytree(os.path.join(H, 'pair'), FIX3)
open(os.path.join(FIX3, 'stray_quotes.csv.partial'), 'w').write('x')
t('T19: an orphan .csv.partial fails capture readiness',
  'ORPHAN_PARTIAL' in
  {c for c, _ in AU.audit_capture(FIX3)['failures']})
FIX4 = os.path.join(WORK, 'fix20')
shutil.copytree(os.path.join(H, 'pair'), FIX4)
m2 = AU.discover_manifests(FIX4)[0]
shutil.copy(m2, m2.replace('_manifest.json',
                           '_manifest.collision-1.json'))
cap4 = AU.audit_capture(FIX4)
t('T20: collision manifests ARE discovered and audited (duplicate '
  'runId reported); no scanner-invisible .json.collision-N names',
  len(AU.discover_manifests(FIX4)) ==
  len(AU.discover_manifests(os.path.join(H, 'pair'))) + 1 and
  'RESTART_COLLISION' in {c for c, _ in cap4['failures']} and
  not glob.glob(os.path.join(H, '*', '*.json.collision-*')))

# ---- build 1.2.1 repairs (exposed by the first genuine sessions) ----
# 23: run-lifetime depth maxima survive a reconnect
lv = runs_of('lvlrun')[0]
lvm = lv['manifest']
t('T23: run-lifetime depth maxima survive a reconnect (seen 2/2 post-'
  'reconnect, run 3/3, build 1.2.2, BOOK_READY once, audit clean)',
  lv['ok'] and lvm.get('recorderBuild') == '1.2.2' and
  lvm['maxBidLevelSeen'] == 2 and lvm['maxAskLevelSeen'] == 2 and
  lvm['maxBidLevelRun'] == 3 and lvm['maxAskLevelRun'] == 3 and
  lv['info']['level_semantics'] == 'run' and
  lv['info']['book_ready'] == 1 and lv['info']['depth_max_bid_obs'] == 3)

# 24: legacy 1.2.0 manifests are judged by the only inequality that
# holds (observed >= post-reconnect value); 1.2.1 fields stay strict
res24 = []
for seen, expect in ((2, True), (3, True), (5, False)):
    d24 = os.path.join(WORK, 'legacy%d' % seen)
    shutil.copytree(os.path.join(H, 'lvlrun'), d24)
    mp = AU.discover_manifests(d24)[0]
    m24 = json.load(open(mp))
    for k in ('maxBidLevelRun', 'maxAskLevelRun', 'recorderBuild'):
        m24.pop(k, None)
    m24['maxBidLevelSeen'] = m24['maxAskLevelSeen'] = seen
    json.dump(m24, open(mp, 'w'))
    r24 = AU.audit_run(mp)
    res24.append(r24['ok'] == expect and
                 r24['info']['level_semantics'] == 'legacy_post_reconnect')
d24 = os.path.join(WORK, 'strict')
shutil.copytree(os.path.join(H, 'lvlrun'), d24)
mp = AU.discover_manifests(d24)[0]
m24 = json.load(open(mp))
m24['maxBidLevelRun'] = 9
json.dump(m24, open(mp, 'w'))
r24 = AU.audit_run(mp)
t('T24: legacy manifests tolerated (observed >= post-reconnect) and '
  'rejected when observed < claimed; 1.2.1 run field checked strictly',
  all(res24) and not r24['ok'] and
  'DEPTH_LEVEL_MISMATCH' in {c for c, _ in r24['failures']})

# 25: instance contiguity from (first, last, count, holes) - no seq list
R1 = dict(seq_first=1, seq_last=608, seq_count=605, seq_holes=[605, 606, 607])
R2 = dict(seq_first=605, seq_last=1000, seq_count=395, seq_holes=[608])
R2g = dict(seq_first=605, seq_last=1000, seq_count=394, seq_holes=[608, 700])
R2d = dict(seq_first=600, seq_last=1000, seq_count=401, seq_holes=[])
t('T25: rotation interleave reconciles across runs; a genuine gap and a '
  'cross-run duplicate both fail (no per-seq list kept)',
  AU.instance_seq_contiguous([R1, R2])[0] and
  not AU.instance_seq_contiguous([R1, R2g])[0] and
  not AU.instance_seq_contiguous([R1, R2d])[0] and
  'event_seqs' not in conc[0]['info'])

# 26: pairing over union coverage - a mid-session restart no longer
# reports zero overlap
import datetime as _dt  # noqa: E402
_T = lambda h, m=0: _dt.datetime(2026, 9, 2, h, m, tzinfo=_dt.timezone.utc)
_mk = lambda i, a, b: dict(ok=True, failures=[], info=dict(
    instrument=i, session='20260902', first_recv=a, last_recv=b))
f26, o26 = AU.pair_sessions([_mk('NQ', _T(0), _T(11, 30)),
                             _mk('NQ', _T(11, 34), _T(22)),
                             _mk('MNQ', _T(0), _T(22))])
f26b, _ = AU.pair_sessions([_mk('NQ', _T(0), _T(2)), _mk('MNQ', _T(12), _T(22))])
t('T26: NQ/MNQ pairing uses the union of each instrument\'s runs '
  '(restart -> overlap 0.99+), disjoint windows still fail',
  not f26 and o26['20260902']['overlap_frac'] > 0.99 and
  o26['20260902']['nq_runs'] == 2 and
  [c for c, _ in f26b] == ['NQ_MNQ_INSUFFICIENT_OVERLAP'])


# 27: streaming audit of a session-shaped run stays flat in memory
from mles_v12_synth import synth_run  # noqa: E402


import tracemalloc  # noqa: E402
mp27 = synth_run(os.path.join(WORK, 'synth'), 300000)
tracemalloc.start()
r27 = AU.audit_run(mp27)
_, peak27 = tracemalloc.get_traced_memory()
tracemalloc.stop()
t('T27: streaming audit of a 300k-depth-row synthetic run is clean with '
  'Python peak allocation < 40 MB (1.2.0 materialised every row)',
  r27['ok'] and r27['info']['events'] > 300000 and peak27 < 40e6 and
  not r27['info']['seq_holes'])

# 28: recv-exch latency is summarised from a fixed 1 ms histogram
pr = runs_of('pair')[0]['info']
t('T28: per-run recv-exch latency summary present (p50/p95/n) without '
  'storing per-event values',
  isinstance(pr.get('latency_ms'), dict) and
  all(k in pr['latency_ms'] for k in ('p50', 'p95', 'n')) and
  pr['latency_ms']['n'] > 0)

# 21: deployment documents name only v1.2 as the install target
docs = ''
for fn in ('RECORDER_DEPLOYMENT_V12.md', 'SETUP_WALKTHROUGH_V12.md',
           'DATA_HANDOFF_V12.md'):
    docs += open(os.path.join(HERE, fn)).read()
old_ok = True
for ln in docs.splitlines():
    if ('MlesV1CaptureHost' in ln or 'MlesV11CaptureHost' in ln):
        if not any(w in ln.lower() for w in
                   ('archive', 'immutable', 'lineage', 'do not')):
            old_ok = False
t('T21: authoritative docs install ONLY MlesV12CaptureHost (older '
  'names appear only as immutable archive warnings)',
  'MlesV12CaptureHost' in docs and old_ok)

# 22: updated ZIP contains the byte-identical v1.2 recorder
Z = os.path.join(HERE, 'MROF_V1_Engine_v12.zip')
zf = zipfile.ZipFile(Z)
rec = zf.read('MROF_V1_Engine/1_NinjaTrader_Recorder/'
              'MlesV12CaptureHost.cs')
t('T22: updated ZIP ships the byte-identical v1.2 recorder as the '
  'authoritative install',
  hashlib.sha256(rec).hexdigest() ==
  sha(os.path.join(ROOT, 'src', 'MlesV12CaptureHost.cs')))
zr = zf.read('MROF_V1_Engine/README.txt').decode()
t('T22b: ZIP README names v1.2 as the install and marks older '
  'recorders as archive',
  'MlesV12CaptureHost' in zr and 'archive_immutable_lineage' in zr)

# T29: BOOK_READY_WITHOUT_RESYNC is an off-by-one on the run that BEGINS
# an instance. Such a run builds its book from nothing, so one
# un-preceded BOOK_READY is legitimate; the allowance is exactly one and
# never more. The first genuine multi-session captures failed every R001
# and passed every R002 - the signature of a bad rule, not of bad data.
def _ready_fails(dirname, extra):
    dd = os.path.join(WORK, dirname)
    mp = SY.synth_run(dd, n_depth=3000, cid='br%d' % extra,
                      session='20260902', extra_book_ready=extra)
    r = AU.audit_run(mp)
    return ([c for c, _ in r['failures']
             if c == 'BOOK_READY_WITHOUT_RESYNC'], r, mp)


f0, r0, m0 = _ready_fails('br0', 0)      # ready 1, resync 1
f1, r1, m1 = _ready_fails('br1', 1)      # ready 2, resync 1  <- the R001 case
f2, r2, _m = _ready_fails('br2', 2)      # ready 3, resync 1  <- genuinely wrong
t('T29: a first run of an instance may carry ONE BOOK_READY with no '
  'preceding resync, and the allowance is exactly one - a second '
  'un-preceded ready still fails',
  not f0 and not f1 and len(f2) == 1 and
  r1['info']['book_ready'] == 2 and
  r1['info']['book_ready_allowed'] == 2 and
  r2['info']['book_ready_allowed'] == 2)

t('T29b: the allowance is tied to firstEventSeq == 1, so a continuation '
  'run gets no free ready',
  json.load(open(m1))['firstEventSeq'] == 1 and
  r0['info']['book_ready_allowed'] == r0['info']['book_resync_starts'] + 1)

# T30: an instance whose later run is still an unfinalized .csv.partial
# leaves a SHORT union - those rows carry a published seq but reach no
# manifest. That is unverifiable, not a detected gap, and calling it a
# gap names the wrong cause. The real 2026-09-09 capture showed exactly
# this on build 1.2.1, which is how the misdiagnosis surfaced.
CID30 = '20260908224314916-aa4a2af2'


def _two_run_instance(dirname, cid, partial, fresh=False):
    dd = os.path.join(WORK, dirname)
    SY.synth_run(dd, n_depth=1500, cid=cid, run_no=1, session='20260909')
    m1 = json.load(open(glob.glob(os.path.join(dd, '*R001_manifest.json'))[0]))
    # R002 resumes 3 seqs later: the two in between are the rows that a
    # still-open rotation is holding
    SY.synth_run(dd, n_depth=1500, cid=cid, run_no=2, session='20260909',
                 seq_start=m1['lastEventSeq'] + 3)
    if partial:
        pp = os.path.join(dd, 'MLES12_NQ_NQ_SEP26_20260910_%s-R003_'
                              'depth.csv.partial' % cid)
        open(pp, 'w').write('x')
        if not fresh:
            # an ORPHAN is days old; a file written a second ago is what
            # a run being recorded right now looks like (see T30c)
            old = time.time() - 2 * 86400
            os.utime(pp, (old, old))
    return AU.audit_capture(dd)


def _codes(res):
    return [c for c, _ in res['failures']]


c30 = _codes(_two_run_instance('openrun', CID30, True))
c30b = _codes(_two_run_instance('closedrun', '20260908224314916-bbbbbbbb',
                                False))
t('T30: a short union on an instance with an unfinalized run reports '
  'UNVERIFIABLE_OPEN_RUN, not a gap, and the orphan partial is still '
  'reported separately',
  'INSTANCE_SEQ_UNVERIFIABLE_OPEN_RUN' in c30 and
  'INSTANCE_SEQ_GAP' not in c30 and 'ORPHAN_PARTIAL' in c30)
t('T30b: the identical shortfall with NO unfinalized run stays a genuine '
  'INSTANCE_SEQ_GAP, so the reclassification cannot hide one',
  'INSTANCE_SEQ_GAP' in c30b and
  'INSTANCE_SEQ_UNVERIFIABLE_OPEN_RUN' not in c30b)

# T30c: the same open run while it is BEING RECORDED -- the state of every
# audit taken during a session. 2026-09-21's audit carried 10 failures
# for exactly this (the live NQ/MNQ run's 8 files and 2 instance
# shortfalls): noise on every weekly check, which is how real failures
# stop being read. The auditor now asks the recovery tool's liveness
# rule -- the same one that must pass before anything is written -- so
# the two can never disagree about which run is live.
r30c = _two_run_instance('liverun', '20260908224314916-cccccccc', True,
                         fresh=True)
c30c = _codes(r30c)
t('T30c: a run still being recorded is reported OPEN, not failed -- no '
  'ORPHAN_PARTIAL, no UNVERIFIABLE_OPEN_RUN, no GAP -- and both its '
  'files and its instance shortfall are named in the report',
  'ORPHAN_PARTIAL' not in c30c and
  'INSTANCE_SEQ_UNVERIFIABLE_OPEN_RUN' not in c30c and
  'INSTANCE_SEQ_GAP' not in c30c and
  '20260908224314916-cccccccc-R003' in
  r30c['info']['open_runs_in_progress'] and
  any('cccccccc' in x
      for x in r30c['info']['instance_shortfall_in_progress']) and
  'OPEN (being recorded, not a failure)' in AU.summary(r30c))

# ---- T34: an unreadable capture is STOPPED, never reported ----------
# 2026-09-22: a loose external drive failed a runner, pilot and wave-two
# pass mid-read, and the wave-two pass printed a clean report of zero
# fires on zero sessions. A folder that cannot be read, or holds nothing,
# is never a result.
empty34 = os.path.join(WORK, 'empty34')
os.makedirs(empty34)
r34 = AU.audit_capture(empty34)
try:
    AU.audit_capture(os.path.join(WORK, 'no_such_drive'))
    gone34 = False
except AU.CaptureUnavailable:
    gone34 = True
t('T34: a readable folder with no manifest is a NO_MANIFESTS failure, '
  'and a folder that cannot be read raises instead of printing an audit',
  'NO_MANIFESTS' in _codes(r34) and not r34['ok'] and gone34 and
  AU.main([os.path.join(WORK, 'no_such_drive')]) == 2)

FIX34 = os.path.join(WORK, 'fix34')
shutil.copytree(os.path.join(H, 'pair'), FIX34)
_v34 = json.load(open(AU.discover_manifests(FIX34)[0]))['depth']['file']
_real_sha = AU.sha256


def _flaky(p):
    if os.path.basename(p) == _v34:
        raise OSError(5, 'Input/output error')
    return _real_sha(p)


AU.sha256 = _flaky
try:
    r34b = AU.audit_capture(FIX34)
finally:
    AU.sha256 = _real_sha
t('T34b: a read error on ONE file while the folder still answers is that '
  'run\'s IO_ERROR; the audit carries on and reports the rest',
  any(c == 'IO_ERROR' for r in r34b['runs'] for c, _ in r['failures']) and
  any(r['ok'] for r in r34b['runs']))

FIX34c = os.path.join(WORK, 'fix34c')
shutil.copytree(os.path.join(H, 'pair'), FIX34c)
_v34c = json.load(open(AU.discover_manifests(FIX34c)[0]))['depth']['file']


def _unplug(p):
    if os.path.basename(p) == _v34c:
        os.rename(FIX34c, FIX34c + '_unplugged')      # the drive vanishes
        raise OSError(22, 'Invalid argument')         # what Windows said
    return _real_sha(p)


AU.sha256 = _unplug
try:
    AU.audit_capture(FIX34c)
    stop34 = False
except AU.CaptureUnavailable as _e:
    stop34 = 'stopped answering' in str(_e)
finally:
    AU.sha256 = _real_sha
t('T34c: the same read error with the FOLDER gone -- the drive unplugged '
  'mid-pass, Errno 22 as on 2026-09-22 -- stops the audit with a plain '
  'reason instead of reporting every later run as missing',
  stop34)

# ---- T35: has the 1.2.2 repair been EXERCISED, or just not contradicted
# Zero spurious readies on 1.2.2 and six on older builds reads like proof,
# but the old sessions ARE the old-build sessions, so build is confounded
# with the calendar -- the operator caught this. The repair acts only
# after a feed disconnect, so the audit now counts that trigger.
def _ev(build, disc, spur, read=True):
    i = dict(recorder_build=build)
    if read:
        i.update(disconnects=disc, spurious_book_ready=spur)
    return dict(info=i)


_rv = AU.repair_evidence
t('T35: the verdict is on the TRIGGER: repaired-build runs with no '
  'disconnect are NOT_EXERCISED however clean they look; with '
  'disconnects and no spurious ready, EXERCISED_AND_HELD; any spurious '
  'ready on a repaired build, FAILED; old builds never count toward it; '
  'an unreadable run is counted, never assumed clean',
  _rv([_ev('1.2.2', 0, 0), _ev('1.2.1', 4, 6)])['repaired']['verdict'] ==
  'NOT_EXERCISED' and
  _rv([_ev('1.2.2', 2, 0)])['repaired']['verdict'] ==
  'EXERCISED_AND_HELD' and
  _rv([_ev('1.2.2', 2, 1)])['repaired']['verdict'] == 'FAILED' and
  _rv([_ev('1.2.1', 4, 6)])['repaired']['verdict'] ==
  'NO_REPAIRED_RUN_READ' and
  _rv([_ev('1.2.2', 0, 0), _ev('1.2.2', 0, 0, read=False)])['repaired']
  == dict(runs=2, read=1, disconnects=0, runs_with_disconnect=0,
          spurious_book_ready=0, verdict='NOT_EXERCISED'))

_dcv = _dc['info']['repair_evidence']['repaired']
t('T35b: end to end on the REAL recorder code -- the mono harness run '
  'with a feed disconnect/reconnect, built from src/ -- the audit counts '
  'the disconnect, finds no spurious ready, and says the repair was '
  'exercised and held; the synthetic fixtures with extra readies count '
  'them as spurious',
  _dcv['disconnects'] >= 1 and _dcv['verdict'] == 'EXERCISED_AND_HELD'
  and 'exercised and held' in AU.summary(_dc) and
  r2['info']['spurious_book_ready'] == 1 and
  r0['info']['spurious_book_ready'] == 0 and
  r0['info']['disconnects'] == 0)

# adapter honesty checks
t('adapter: v1.2 schema requires captureInstanceId column',
  AD.HEADER_COMMON[1] == 'captureInstanceId')
try:
    AD._common(dict(schema=AD.SCHEMA, captureInstanceId='x', runId='r',
                    segId='1', session='s', instrument='NQ',
                    contract='c', stream='SWEEP', eventSeq='1',
                    streamSeq='1', tRecvUtc='', tExchUtc='',
                    tMono='1'), 'quotes')
    bad = False
except AD.UnknownEnumError:
    bad = True
t('adapter: unknown stream enum rejected, never silently ignored', bad)


# ---- T32: depth completeness needs enough depth rows to assert -------
# Two genuine runs tripped MISSING_DEPTH_ACTION in the first nine
# recorded sessions -- 20260905 (608 rows; the market was shut at 18:04
# ET Friday) and 20260908 (70 rows). A run that small legitimately never
# sees a REMOVE, so failing it is a false positive. The rule now needs
# 20 * declaredDepth depth rows before it asserts anything; a live NQ
# run carries tens of millions, so no feed defect can hide behind it.
def _strip_removes(d):
    """Drop every REMOVE depth row and re-stamp the manifest so the run
    is self-consistent apart from the genuinely absent action."""
    mp = glob.glob(os.path.join(d, '*_manifest.json'))[0]
    man = json.load(open(mp))
    dp = os.path.join(d, man['depth']['file'])
    rows = open(dp).read().splitlines(True)
    keep = [rows[0]] + [r for r in rows[1:] if ',REMOVE,' not in r]
    open(dp, 'w').writelines(keep)
    man['depth'].update(rows=len(keep) - 1, bytes=os.path.getsize(dp),
                        sha256=sha(dp))
    json.dump(man, open(mp, 'w'))
    return mp


_small = os.path.join(WORK, 'dsmall')
_big = os.path.join(WORK, 'dbig')
SY.synth_run(_small, n_depth=60, cid='dsmall')     # 60 < 20*10
SY.synth_run(_big, n_depth=4000, cid='dbig')       # 4000 >= 20*10
_rs = AU.audit_run(_strip_removes(_small))
_rb = AU.audit_run(_strip_removes(_big))
_cs = {c for c, _ in _rs['failures']}
_cb = {c for c, _ in _rb['failures']}
t('T32: a near-empty run with a genuinely absent REMOVE does NOT raise '
  'MISSING_DEPTH_ACTION, and says the check was skipped',
  'MISSING_DEPTH_ACTION' not in _cs and
  _rs['info']['depth_completeness_checked'] is False and
  'depth_completeness_skipped' in _rs['info'])
t('T32b: the identical absence in a run with enough depth rows STILL '
  'fails, so the guard cannot hide a real feed defect',
  'MISSING_DEPTH_ACTION' in _cb and
  _rb['info']['depth_completeness_checked'] is True and
  'REMOVE' not in _rb['info']['depth_actions'])


# ---- T32c/d: completeness is a claim about churn on a BUILT book -----
# A 228-row restart stub (NQ, 20260913) still tripped the first floor:
# ~60 of its rows were the book being built, when only ADDs can occur.
# So the floor now counts depth rows AFTER the run's first BOOK_READY,
# and a run that never reached BOOK_READY can support no completeness
# claim at all.
def _strip_quality_kind(d, kind):
    mp = glob.glob(os.path.join(d, '*_manifest.json'))[0]
    man = json.load(open(mp))
    qp = os.path.join(d, man['quality']['file'])
    rows = open(qp).read().splitlines(True)
    keep = [rows[0]] + [r for r in rows[1:] if (',%s,' % kind) not in r]
    open(qp, 'w').writelines(keep)
    man['quality'].update(rows=len(keep) - 1, bytes=os.path.getsize(qp),
                          sha256=sha(qp))
    json.dump(man, open(mp, 'w'))
    return mp


_noready = os.path.join(WORK, 'dnoready')
SY.synth_run(_noready, n_depth=4000, cid='dnoready')
_rn = AU.audit_run(_strip_quality_kind(_noready, 'BOOK_READY'))
_cn = {c for c, _ in _rn['failures']}
t('T32c: a run that never reached BOOK_READY built no book, so sides/'
  'actions are not asserted even with thousands of depth rows, and the '
  'skip says why',
  'MISSING_DEPTH_ACTION' not in _cn and
  _rn['info']['depth_completeness_checked'] is False and
  'never reached BOOK_READY' in _rn['info']['depth_completeness_skipped']
  and _rn['info']['depth_rows_after_book_ready'] == 0)
t('T32d: on a normal run the post-ready count excludes the rows that '
  'built the book, is still far above the floor, and the check runs',
  0 < _rb['info']['depth_rows_after_book_ready'] <
  _rb['info']['depth_rows'] and
  _rb['info']['depth_completeness_checked'] is True and
  _rs['info']['depth_rows_after_book_ready'] < _rs['info']['depth_rows'])


# ---- T33: the build stamp and the quality-stream repair travel together
# The 2026-09-13 repair changed WHICH QUALITY EVENTS a run emits (gate
# maxima reset on disconnect, plus a BOOK_RESYNC_START there) but was
# first committed without bumping RecorderBuild -- so a manifest written
# by the repaired recorder was indistinguishable from one written by the
# broken one. That defeats the entire purpose of the field, whose own
# comment says builds exist so sessions captured before/after a repair
# stay distinguishable. This test binds them: if the repair is in the
# source, the build must be at least 1.2.2.
_rec = open(os.path.join(ROOT, 'src', 'MlesV12CaptureHost.cs')).read()
_bm = re.search(r'RecorderBuild\s*=\s*"([0-9.]+)"', _rec)
_build = tuple(int(x) for x in _bm.group(1).split('.')) if _bm else ()
_disco = re.search(r'run\.BookReady = false;.*?Quality\(ev\.RecvUtc,\s*'
                   r'"DISCONNECT"', _rec, re.S)
_has_repair = bool(_disco) and 'run.MaxBidLvl = run.MaxAskLvl = -1;' in \
    _disco.group(0)
t('T33: the disconnect BOOK_READY repair is present AND RecorderBuild '
  'is >= 1.2.2, so a manifest always says which behaviour produced it',
  _has_repair and _build >= (1, 2, 2))
t('T33b: the live harness run stamps the bumped build, so real captures '
  'are attributable',
  lvm.get('recorderBuild') == _bm.group(1))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
