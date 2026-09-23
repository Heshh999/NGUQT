#!/usr/bin/env python3
# MROF-YT-RECOVER-1.4 suite. Manifest reconstruction for runs whose
# recorder died before finalizing. Exercised on synthetic recorder-format
# runs (mles_v12_synth) damaged in the specific ways a power loss causes.
# Synthetic events verify CODE BEHAVIOR only, never market evidence.
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_adapter as AD     # noqa: E402
import mles_v12_audit as AU       # noqa: E402
import mles_v12_synth as SY       # noqa: E402
import mrofyt_recover as RC       # noqa: E402
import mrofyt_runner as RN        # noqa: E402

# The drive each test simulates is stated, not inherited from whatever
# machine runs the suite (this sandbox has ~30 GB free, below the 40 GB
# reserve). V1-V9 simulate a roomy drive; V10 sets its own numbers.
_REAL_FREE_BYTES = RC._free_bytes
RC._free_bytes = lambda d: 10 ** 13                   # a 10 TB-free drive

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_rec_')


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def make_run(sub, **kw):
    d = os.path.join(WORK, sub)
    mp = SY.synth_run(d, n_depth=kw.pop('n_depth', 8000), **kw)
    return d, mp


OLD = time.time() - 2 * 86400


def age(d):
    """A real orphan is DAYS old. Fixtures are written seconds before
    they are read, which is exactly what a run being recorded right now
    looks like, so every dead-run fixture is aged explicitly and the
    live-run tests (V8) are the only ones left fresh."""
    for p in glob.glob(os.path.join(d, '*.csv*')):
        os.utime(p, (OLD, OLD))


def orphan(d, mp, rename_partial=(), age_files=True):
    """Delete the manifest (what an ungraceful death leaves behind) and
    optionally put some streams back into .partial form."""
    man = json.load(open(mp))
    os.remove(mp)
    for k in rename_partial:
        p = os.path.join(d, man[k]['file'])
        os.rename(p, p + '.partial')
    if age_files:
        age(d)
    return man


# ---------------------------------------------------------------------
# V1: a complete run that merely lost its manifest
# ---------------------------------------------------------------------
d1, mp1 = make_run('clean', cid='v1cid', session='20260915')
orig1 = json.load(open(mp1))
before1 = {k: sha(os.path.join(d1, orig1[k]['file'])) for k in AD.STREAMS}
orphan(d1, mp1)

found = RC.find_orphan_runs(d1)
t('V1: a run whose manifest is gone is found as exactly one orphan, '
  'with all four streams and nothing missing',
  len(found) == 1 and found[0]['run_id'] == orig1['runId'] and
  sorted(found[0]['streams']) == sorted(AD.STREAMS) and
  found[0]['missing'] == [] and found[0]['partial'] is False)

r1 = RC.reconstruct(d1, found[0])
new1 = json.load(open(os.path.join(d1, r1['manifest'])))
t('V1b: it reconstructs, and every count/bound recomputed from the rows '
  'equals what the recorder originally wrote',
  r1['status'] == 'RECONSTRUCTED' and
  new1['firstEventSeq'] == orig1['firstEventSeq'] and
  new1['lastEventSeq'] == orig1['lastEventSeq'] and
  all(new1[k]['rows'] == orig1[k]['rows'] for k in AD.STREAMS) and
  all(new1[k]['sha256'] == orig1[k]['sha256'] for k in AD.STREAMS) and
  new1['depthBid'] == orig1['depthBid'] and
  new1['depthRemove'] == orig1['depthRemove'] and
  new1['maxBidLevelRun'] == orig1['maxBidLevelRun'])

t('V1c: the recorder\'s self-reported integrity counters are ABSENT, '
  'never invented as zero -- nothing in the rows can reveal them',
  all(c not in new1 for c in RC.NEVER_INVENTED) and
  new1['reconstructed'] is True and
  new1['closeReason'] == RC.CLOSE_REASON and
  'ABSENT, not zero' in new1['reconstructionNote'] and
  'nothing in the rows can reveal them' in new1['reconstructionNote'])

t('V1d: reconstruction never modifies the original CSVs',
  all(sha(os.path.join(d1, orig1[k]['file'])) == before1[k]
      for k in AD.STREAMS))

led1 = RN.Runner(d1, ('NQ',)).run()
t('V1e: the recovered run is now INGESTIBLE -- the runner reads it '
  'instead of skipping it, which is the whole point',
  led1['totals']['events'] == orig1['lastEventSeq'] and
  not led1['skipped_runs'])

aud1 = AU.audit_run(os.path.join(d1, r1['manifest']))
codes1 = {c for c, _ in aud1['failures']}
t('V1f: the auditor reports it as NOT SELF-VERIFYING rather than a '
  'clean pass, and does not bury it in MISSING_COUNTER noise',
  'RECONSTRUCTED_RUN_NOT_SELF_VERIFYING' in codes1 and
  'MISSING_COUNTER' not in codes1 and
  aud1['info']['reconstructed'] is True and aud1['ok'] is False)

cap1 = AU.audit_capture(d1)
t('V1g: once reconstructed, its CSVs are no longer reported as orphans',
  not any(c == 'ORPHAN_FINALIZED_CSV' for c, _ in cap1['failures']))

# ---------------------------------------------------------------------
# V2: a run cut off mid-row, the way a power loss actually leaves it
# ---------------------------------------------------------------------
d2, mp2 = make_run('cut', cid='v2cid', session='20260916')
orig2 = json.load(open(mp2))
orphan(d2, mp2, rename_partial=AD.STREAMS)
qp = os.path.join(d2, orig2['quotes']['file'] + '.partial')
with open(qp, 'a') as fh:
    fh.write('MLES-CAPTURE-1.2,v2cid,')          # a half-written row
age(d2)
before2 = sha(qp)

f2 = RC.find_orphan_runs(d2)
r2_no = RC.reconstruct(d2, f2[0])
t('V2: a damaged stream is NOT silently rewritten -- without --repair '
  'the run reports NEEDS_REPAIR and names the bad row',
  r2_no['status'] == 'NEEDS_REPAIR' and 'quotes' in r2_no['damaged'] and
  'no newline' in r2_no['damaged']['quotes'][1] and not r2_no['written'])

r2_dry = RC.recover_directory(d2, dry_run=True)['results'][0]
t('V2b: --dry-run spots the damaged tail, says repair is needed, and '
  'writes nothing',
  r2_dry['status'] == 'WOULD_RECONSTRUCT_WITH_REPAIR' and
  'quotes' in r2_dry['damaged_tail'] and not r2_dry['written'] and
  not any(x.endswith('_RECOVERED.csv') for x in os.listdir(d2)))

r2 = RC.reconstruct(d2, f2[0], repair=True)
new2 = json.load(open(os.path.join(d2, r2['manifest'])))
t('V2c: with --repair it writes NEW _RECOVERED files, leaves the damaged '
  'original byte-for-byte untouched, and references only the new ones',
  r2['status'] == 'RECONSTRUCTED' and sha(qp) == before2 and
  all(new2[k]['file'].endswith('_RECOVERED.csv') for k in AD.STREAMS) and
  all(os.path.exists(os.path.join(d2, new2[k]['file']))
      for k in AD.STREAMS))

# the critical property: ONE common cut point across all four streams
cuts = {}
for k in AD.STREAMS:
    p = os.path.join(d2, new2[k]['file'])
    last = open(p).read().rstrip('\n').rsplit('\n', 1)[-1].split(',')
    cuts[k] = int(last[AD.HEADERS[k].index('eventSeq')])
t('V2d: every stream is truncated to ONE common eventSeq, so a repaired '
  'run can never leave quotes running past the last depth update',
  max(cuts.values()) <= new2['lastEventSeq'] and
  new2['lastEventSeq'] == max(cuts.values()) and
  all(v <= new2['lastEventSeq'] for v in cuts.values()))

aud2 = AU.audit_run(os.path.join(d2, r2['manifest']))
codes2 = {c for c, _ in aud2['failures']}
t('V2e: the repaired run is internally consistent -- no hash, byte, row '
  'or sequence mismatch survives the rewrite',
  not ({'HASH_MISMATCH', 'BYTE_SIZE_MISMATCH', 'STREAM_ROW_MISMATCH',
        'FIRST_EVENT_SEQ_MISMATCH', 'LAST_EVENT_SEQ_MISMATCH',
        'MALFORMED_HEADER'} & codes2))

led2 = RN.Runner(d2, ('NQ',)).run()
t('V2f: and the runner ingests the repaired run without the '
  'STREAM_SIZE_MISMATCH or CORRUPT_STREAM guards firing',
  led2['totals']['events'] > 0 and not led2['skipped_runs'])

# ---------------------------------------------------------------------
# V3: refusals -- the cases where reconstructing would be wrong
# ---------------------------------------------------------------------
d3, mp3 = make_run('incomplete', cid='v3cid', session='20260917')
man3 = json.load(open(mp3))
os.remove(mp3)
os.remove(os.path.join(d3, man3['trades']['file']))
age(d3)
r3 = RC.reconstruct(d3, RC.find_orphan_runs(d3)[0])
t('V3: a run missing a whole stream is refused, not papered over -- the '
  'runner would skip it anyway and a manifest would only hide that',
  r3['status'] == 'SKIPPED_INCOMPLETE_RUN' and r3['missing'] == ['trades']
  and not r3['written'])

d4, mp4 = make_run('empty', cid='v4cid', session='20260917')
man4 = json.load(open(mp4))
os.remove(mp4)
dp = os.path.join(d4, man4['depth']['file'])
open(dp, 'w').write(','.join(AD.HEADERS['depth']) + '\n')   # header only
age(d4)
r4 = RC.reconstruct(d4, RC.find_orphan_runs(d4)[0], repair=True)
t('V4: a stream with a header but no rows yields no manifest at all',
  r4['status'] == 'SKIPPED_NO_USABLE_ROWS' and
  'depth' in r4['empty_streams'] and not r4['written'])

# ---------------------------------------------------------------------
# V5: the declared (not observed) fields come from a verified sibling
# ---------------------------------------------------------------------
d5 = os.path.join(WORK, 'sibling')
SY.synth_run(d5, n_depth=6000, cid='sibcid', session='20260915', run_no=1)
mp5b = SY.synth_run(d5, n_depth=6000, cid='sibcid', session='20260915',
                    run_no=2)
orphan(d5, mp5b)
r5 = RC.reconstruct(d5, RC.find_orphan_runs(d5)[0])
new5 = json.load(open(os.path.join(d5, r5['manifest'])))
t('V5: declarations that cannot be observed (declaredDepth, build, '
  'aggressorSource) are taken from a sibling of the SAME capture '
  'instance, and the source run is recorded',
  new5['declaredDepth'] == 10 and new5['recorderBuild'] == '1.2.1' and
  'inferred' in new5['aggressorSource'] and
  new5['reconstructedFieldsFrom'] == 'sibcid-R001' and
  'declaredDepthInferred' not in new5)

d6, mp6 = make_run('nosibling', cid='lonecid', session='20260918')
orphan(d6, mp6)
r6 = RC.reconstruct(d6, RC.find_orphan_runs(d6)[0])
new6 = json.load(open(os.path.join(d6, r6['manifest'])))
t('V5b: with no sibling, declaredDepth is inferred from the deepest '
  'level seen and is LABELLED as inferred rather than passed off as '
  'declared',
  new6.get('declaredDepthInferred') is True and
  new6['declaredDepth'] == 10 and
  'reconstructedFieldsFrom' not in new6)

# ---------------------------------------------------------------------
# V6: a run that already has a manifest is never touched
# ---------------------------------------------------------------------
d7, mp7 = make_run('intact', cid='v7cid', session='20260915')
t('V6: a run with a valid manifest is not an orphan and is left alone',
  RC.find_orphan_runs(d7) == [] and
  RC.recover_directory(d7)['orphan_runs'] == 0)

# ---------------------------------------------------------------------
# V7: a dry run must be CHEAP. It probes the header and the tail only,
# never the middle, so listing what is recoverable costs the same on a
# 6 GB depth file as on a small one. (The first implementation scanned
# every row even for --dry-run, which made "just show me what's there"
# a 30-minute operation on a real capture folder.)
# ---------------------------------------------------------------------
d8, mp8 = make_run('probe', cid='v8cid', session='20260915', n_depth=20000)
man8 = json.load(open(mp8))
orphan(d8, mp8)
dp8 = os.path.join(d8, man8['depth']['file'])
size8 = os.path.getsize(dp8)

reads = {'n': 0}
_real_open = open


class _CountingFile(object):
    """Counts every byte handed out. __enter__/__exit__/__iter__ are
    spelled out because Python looks dunders up on the TYPE, so
    __getattr__ never sees them."""

    def __init__(self, f):
        self._f = f

    def _count(self, b):
        reads['n'] += len(b) if b else 0
        return b

    def read(self, *a):
        return self._count(self._f.read(*a))

    def readline(self, *a):
        return self._count(self._f.readline(*a))

    def __iter__(self):
        for line in self._f:
            yield self._count(line)

    def __enter__(self):
        self._f.__enter__()
        return self

    def __exit__(self, *a):
        return self._f.__exit__(*a)

    def __getattr__(self, k):
        return getattr(self._f, k)


import builtins  # noqa: E402


def _counting_open(path, *a, **kw):
    f = _real_open(path, *a, **kw)
    return _CountingFile(f) if str(path).endswith('.csv') else f


builtins.open = _counting_open
try:
    pr = RC.recover_directory(d8, dry_run=True)
finally:
    builtins.open = _real_open

t('V7: a dry run probes header+tail only -- it reads far less than the '
  'depth file it reports on, instead of streaming every row',
  reads['n'] < size8 / 2 and pr['orphan_runs'] == 1 and
  pr['results'][0]['status'] == 'WOULD_RECONSTRUCT')

t('V7b: and it still reports the size and per-stream verdict needed to '
  'decide what is worth recovering',
  pr['results'][0]['bytes_total'] > size8 and
  all(v['ends_cleanly'] for v in pr['results'][0]['streams'].values()) and
  'GB' in RC.text_summary(pr))

t('V7c: the dry run wrote nothing -- no manifest, no _RECOVERED file',
  not any(x.endswith(('_RECONSTRUCTED_manifest.json', '_RECOVERED.csv'))
          for x in os.listdir(d8)))

# ---------------------------------------------------------------------
# V8: a run STILL BEING WRITTEN has no manifest either. 1.0 listed
# today's live NQ and MNQ runs (8.76 + 7.79 GB, .partial, ending
# mid-flush) as "damaged, needs --repair" on the first real folder it
# saw. A live run must be named, counted apart, and refused by every
# path -- dry-run, plain, --repair, and a direct reconstruct() call.
# ---------------------------------------------------------------------
d9 = os.path.join(WORK, 'live')
mp9 = SY.synth_run(d9, n_depth=6000, cid='livecid', session='20260915')
man9 = orphan(d9, mp9, rename_partial=AD.STREAMS, age_files=False)
live_paths = [os.path.join(d9, man9[k]['file'] + '.partial')
              for k in AD.STREAMS]
with open(live_paths[0], 'a') as fh:
    fh.write('MLES-CAPTURE-1.2,livecid,')      # flush in progress
live_sha = {p: sha(p) for p in live_paths}

f9 = RC.find_orphan_runs(d9)
pr9 = RC.recover_directory(d9, dry_run=True)
s9 = RC.text_summary(pr9)
t('V8: a run written seconds ago is reported SKIPPED_LIVE_RUN by the '
  'dry run -- not as damaged -- counted apart from orphans, and its '
  'bytes are NOT counted as recoverable',
  len(f9) == 1 and f9[0]['live'] and 'still being written' in f9[0]['live']
  and pr9['orphan_runs'] == 0 and pr9['live_runs'] == 1 and
  pr9['results'][0]['status'] == 'SKIPPED_LIVE_RUN' and
  'NOT orphans, left alone): 1' in s9 and 'recoverable data' not in s9)

rr9 = RC.recover_directory(d9, repair=True)
direct9 = RC.reconstruct(d9, f9[0], repair=True)
t('V8b: --repair on a live run writes nothing and reads nothing in bulk, '
  'and a direct reconstruct() call is refused the same way, so no path '
  'can pin a manifest on a run the recorder still owns',
  rr9['results'][0]['status'] == 'SKIPPED_LIVE_RUN' and
  direct9['status'] == 'SKIPPED_LIVE_RUN' and not direct9['written'] and
  not any(x.endswith(('_RECONSTRUCTED_manifest.json', '_RECOVERED.csv'))
          for x in os.listdir(d9)) and
  all(sha(p) == h for p, h in live_sha.items()))

# a dead orphan beside the live run is still recovered
mp9b = SY.synth_run(d9, n_depth=6000, cid='deadcid', session='20260915')
orphan(d9, mp9b)                                 # aged
os.utime(live_paths[0], None)                    # keep the live one fresh
for p in live_paths[1:]:
    os.utime(p, None)
rr9b = RC.recover_directory(d9, repair=True)
by9 = {r['run_id']: r['status'] for r in rr9b['results']}
t('V8c: an aged orphan beside the live run is reconstructed while the '
  'live run beside it is still left alone -- the refusal is per run, '
  'not per folder',
  by9.get('deadcid-R001') == 'RECONSTRUCTED' and
  by9.get('livecid-R001') == 'SKIPPED_LIVE_RUN' and
  rr9b['orphan_runs'] == 1 and rr9b['live_runs'] == 1 and
  all(sha(p) == h for p, h in live_sha.items()))

# the second sign: a run whose session label has not closed yet is live
# even when its files are mtime-stale (recorder alive but idle)
d10 = os.path.join(WORK, 'openses')
cur_ses = RN.session_id(time.time())
mp10 = SY.synth_run(d10, n_depth=6000, cid='opencid', session=cur_ses)
orphan(d10, mp10)                                # aged -> mtime is stale
f10_now = RC.find_orphan_runs(d10)
f10_later = RC.find_orphan_runs(d10, now=time.time() + 30 * 86400)
t('V8d: a stale-mtime run whose session label is the CURRENT CME session '
  'is live by the second sign; the same files judged from a clock a '
  'month later are a plain orphan -- the rule reads the clock, not the '
  'label alone',
  f10_now[0]['live'] and 'current CME session' in f10_now[0]['live'] and
  f10_later[0]['live'] is None and
  RC.reconstruct(d10, f10_now[0])['status'] == 'SKIPPED_LIVE_RUN' and
  RC.reconstruct(d10, f10_later[0], now=time.time() + 30 * 86400)['status']
  == 'RECONSTRUCTED')

# ---------------------------------------------------------------------
# V9: the direct check (1.2). On Windows the recorder holds each stream
# open FileAccess.Write + FileShare.Read for the life of the run, and a
# read-only open that refuses to share writing fails for exactly as long
# as it does. It is the only sign that holds over a weekend: the session
# roll is driven by market events, so the open run keeps Friday's label,
# and the recorder writes nothing while the market is closed, so every
# file is byte-for-byte still. 1.1's indirect signs would have rebuilt a
# manifest for that run on Saturday -- the day --repair is meant to run.
# The Windows call cannot run here; these pin every decision around it
# with an injected answer, and V9f pins the recorder-side premise in the
# recorder's own source. The call itself is verified only by a dry run
# on the operator's machine.
# ---------------------------------------------------------------------
def HELD(p):
    return 'HELD'


def FREE(p):
    return 'FREE'


def ERR(p):
    return 'ERROR: Windows error 5'


d11 = os.path.join(WORK, 'weekend')
mp11 = SY.synth_run(d11, n_depth=6000, cid='wkndcid', session='20260918')
orphan(d11, mp11, rename_partial=AD.STREAMS)     # nothing written in days
f11_ind = RC.find_orphan_runs(d11)               # no Windows check here
f11_held = RC.find_orphan_runs(d11, probe=HELD)
t('V9: a run NinjaTrader still holds over a weekend -- an old session '
  'label, nothing written for days -- passes every indirect sign as '
  'dead; the Windows check says it is held, and the check wins',
  f11_ind[0]['live'] is None and
  f11_held[0]['live'] and 'open for writing' in f11_held[0]['live'] and
  f11_held[0]['liveness_by'] == 'windows file-sharing check')

before11 = sorted(os.listdir(d11))
st_held = RC.recover_directory(d11, repair=True, probe=HELD)
st_err = RC.recover_directory(d11, repair=True, probe=ERR)
t('V9b: held -> --repair writes nothing; and a check that FAILS is never '
  'read as "not held" -- an error refuses exactly like a hold',
  st_held['results'][0]['status'] == 'SKIPPED_LIVE_RUN' and
  st_err['results'][0]['status'] == 'SKIPPED_LIVE_RUN' and
  'never read as "not held"' in
  RC.find_orphan_runs(d11, probe=ERR)[0]['live'] and
  sorted(os.listdir(d11)) == before11)

d12 = os.path.join(WORK, 'crashtoday')
mp12 = SY.synth_run(d12, n_depth=6000, cid='crashcid',
                    session=RN.session_id(time.time()))
orphan(d12, mp12)
t('V9c: when Windows answers FREE the session label stops vetoing -- a '
  'run from today that NinjaTrader has released (crash, then restart) '
  'is an orphan now, not after 18:00; with no check it waits (V8d)',
  RC.find_orphan_runs(d12, probe=FREE)[0]['live'] is None and
  'current CME session' in RC.find_orphan_runs(d12)[0]['live'] and
  RC.recover_directory(d12, probe=FREE)['results'][0]['status'] ==
  'RECONSTRUCTED')

d13 = os.path.join(WORK, 'justclosed')
n13 = 4000
now13 = time.time()
mp13 = SY.synth_run(d13, n_depth=n13, cid='closecid', session='20260918',
                    t0=now13 - 30 - n13 * 0.0005)
orphan(d13, mp13, rename_partial=AD.STREAMS)     # modified time looks old
f13 = RC.find_orphan_runs(d13, now=now13, probe=FREE)
f13_later = RC.find_orphan_runs(d13, now=now13 + 1200, probe=FREE)
t('V9d: FREE, but the newest row is 30 s old by the recorder\'s own '
  'clock -- a run the recorder may be closing right now (files released, '
  'manifest not yet written) is left alone; twenty minutes on it is an '
  'orphan',
  f13[0]['live'] and 'stamped' in f13[0]['live'] and
  f13_later[0]['live'] is None)

qp13 = glob.glob(os.path.join(d13, '*_quotes.csv.partial'))[0]
good13 = RC.newest_recv(qp13, 'quotes')
with open(qp13, 'a') as fh:
    fh.write('MLES-CAPTURE-1.2,closecid,closecid-R001,1,2026')   # mid-row
t('V9e: the row clock reads the newest COMPLETE row, so a tail cut '
  'mid-row -- a flush in progress, or a crash -- still dates the run',
  good13 is not None and RC.newest_recv(qp13, 'quotes') == good13 and
  abs(good13 - (now13 - 30)) < 5)

CS = open(os.path.join(HERE, '..', '..', 'src',
                       'MlesV12CaptureHost.cs')).read()
t('V9f: the premise is the recorder\'s own source: streams are opened '
  'FileAccess.Write + FileShare.Read (so a read open refusing write '
  'sharing fails exactly while held), and the session roll is driven by '
  'market events (so a weekend run keeps Friday\'s label). If either '
  'changes, this fails before any folder is misjudged',
  re.search(r'new FileStream\(path, FileMode\.CreateNew,\s*'
            r'FileAccess\.Write, FileShare\.Read\)', CS) is not None and
  'SessionOf(DateTime.UtcNow)' in CS and
  'ev.Session != run.Session' in CS)

d14 = os.path.join(WORK, 'atomic')
mp14 = SY.synth_run(d14, n_depth=4000, cid='atomcid', session='20260916')
orphan(d14, mp14)
RC.recover_directory(d14, probe=FREE)
t('V9g: the reconstructed manifest is written aside and moved into '
  'place, so a drive that drops mid-write leaves an ignored .tmp, never '
  'a half manifest that marks the run done',
  any(x.endswith('_RECONSTRUCTED_manifest.json') for x in os.listdir(d14))
  and not any(x.endswith('.tmp') for x in os.listdir(d14)) and
  'os.replace(tmp, mp)' in open(os.path.join(HERE,
                                             'mrofyt_recover.py')).read())

# ---------------------------------------------------------------------
# V10: a repair must not fill the drive the recorder writes to
# ---------------------------------------------------------------------
d15 = os.path.join(WORK, 'space')
mp15a = SY.synth_run(d15, n_depth=4000, cid='spacea', session='20260914')
mp15b = SY.synth_run(d15, n_depth=4000, cid='spaceb', session='20260915')
orphan(d15, mp15a, rename_partial=AD.STREAMS)            # clean, all .partial
man15b = orphan(d15, mp15b, rename_partial=AD.STREAMS)
dmg15 = os.path.join(d15, man15b['depth']['file'] + '.partial')
with open(dmg15, 'a') as fh:
    fh.write('MLES-CAPTURE-1.2,spaceb,spaceb-R001,1,2026')  # cut mid-row
age(d15)
runs15 = RC.find_orphan_runs(d15, probe=FREE)
size = lambda cid: sum(os.path.getsize(p) for r in runs15          # noqa: E731
                       if cid in r['base'] for p in r['streams'].values())
need15 = size('spacea') + size('spaceb')
dry15 = RC.recover_directory(d15, dry_run=True, probe=FREE)
wp15 = dry15['repair_write_plan']
t('V10: the dry run states what --repair would write -- every .partial '
  'stream of a clean run and every stream of a damaged one, in full -- '
  'against the free space and the 40 GB kept for the recorder',
  wp15['bytes_to_write'] == need15 and wp15['reserve_bytes'] == 40 * 10 ** 9
  and wp15['fits'] is True and
  '--repair would write up to' in RC.text_summary(dry15) and
  RC.write_plan(runs15, dry15['results'], d15, repair=False)[
      'bytes_to_write'] == size('spacea'))

tree15 = {x: sha(os.path.join(d15, x)) for x in sorted(os.listdir(d15))}
RC._free_bytes = lambda d: need15 + RC.RESERVE_BYTES - 1   # one byte short
raised15 = None
try:
    RC.recover_directory(d15, repair=True, probe=FREE)
except RC.InsufficientSpace as exc:
    raised15 = str(exc)
import io                                                   # noqa: E402
import contextlib                                           # noqa: E402
_buf = io.StringIO()
_rf = RC.find_orphan_runs


def _free_probe_find(d, now=None, probe=None):
    return _rf(d, now, FREE)


RC.find_orphan_runs = _free_probe_find
with contextlib.redirect_stdout(_buf):
    rc15 = RC.main([d15, '--repair'])
RC.find_orphan_runs = _rf
t('V10b: one byte short of leaving 40 GB free, --repair stops before '
  'writing anything -- the folder is byte-identical, the CLI prints '
  'STOPPED with the numbers and exits 2',
  raised15 is not None and 'Nothing was written' in raised15 and
  rc15 == 2 and 'STOPPED' in _buf.getvalue() and
  {x: sha(os.path.join(d15, x)) for x in sorted(os.listdir(d15))} == tree15)

RC._free_bytes = lambda d: need15 + RC.RESERVE_BYTES       # exactly enough
direct15 = RC.reconstruct(
    d15, [r for r in runs15 if 'spacea' in r['base']][0], probe=FREE)
RC._free_bytes = lambda d: RC.RESERVE_BYTES               # none to spare
d16 = os.path.join(WORK, 'space2')
mp16 = SY.synth_run(d16, n_depth=3000, cid='spacec', session='20260916')
orphan(d16, mp16, rename_partial=AD.STREAMS)
before16 = sorted(os.listdir(d16))
r16 = RC.reconstruct(d16, RC.find_orphan_runs(d16, probe=FREE)[0],
                     probe=FREE)
RC._free_bytes = _REAL_FREE_BYTES
t('V10c: with exactly enough room the run is reconstructed; a direct '
  'reconstruct() with no room to spare is refused per run as '
  'SKIPPED_NO_SPACE and writes nothing; the real free-space call is the '
  'drive\'s own',
  direct15['status'] == 'RECONSTRUCTED' and
  r16['status'] == 'SKIPPED_NO_SPACE' and
  sorted(os.listdir(d16)) == before16 and
  RC._free_bytes(WORK) == shutil.disk_usage(WORK).free)

# ---------------------------------------------------------------------
# V11: one file the drive will not read must not stop the pass
# ---------------------------------------------------------------------
d17 = os.path.join(WORK, 'unreadable')
mp17a = SY.synth_run(d17, n_depth=3000, cid='badfile', session='20260917')
mp17b = SY.synth_run(d17, n_depth=3000, cid='goodfile', session='20260918')
man17a = orphan(d17, mp17a, rename_partial=AD.STREAMS)
orphan(d17, mp17b)
bad17 = os.path.join(d17, man17a['depth']['file'] + '.partial')
_real_open = open


def _open_like_a_dropped_drive(p, *a, **kw):
    if os.path.abspath(str(p)) == os.path.abspath(bad17):
        e = OSError(22, 'Invalid argument')
        e.winerror = 1392                      # ERROR_FILE_CORRUPT
        raise e
    return _real_open(p, *a, **kw)


RC._free_bytes = lambda d: 10 ** 13                   # a roomy drive again
RC.open = _open_like_a_dropped_drive
try:
    dry17 = RC.recover_directory(d17, dry_run=True, probe=FREE)
    before17 = sorted(os.listdir(d17))
    real17 = RC.recover_directory(d17, repair=True, probe=FREE)
finally:
    del RC.open
by17 = {r['run_id']: r for r in dry17['results']}
byr17 = {r['run_id']: r for r in real17['results']}
t('V11: a file the drive will not read (Python says errno 22) does not '
  'stop the pass: the dry run names the file with its Windows error and '
  'sets that run aside as SKIPPED_UNREADABLE_FILE, the other run is '
  'still reconstructed, and nothing is written for the unreadable one',
  by17['badfile-R001']['status'] == 'SKIPPED_UNREADABLE_FILE' and
  'Windows error 1392' in list(by17['badfile-R001']['unreadable'].values())[0]
  and os.path.basename(bad17) in by17['badfile-R001']['unreadable'] and
  by17['goodfile-R001']['status'] == 'WOULD_RECONSTRUCT' and
  byr17['badfile-R001']['status'] == 'SKIPPED_UNREADABLE_FILE' and
  byr17['goodfile-R001']['status'] == 'RECONSTRUCTED' and
  not any(x.startswith(man17a['depth']['file'][:20]) and 'RECOVERED' in x
          for x in os.listdir(d17)) and
  'Windows error 1392' in RC.text_summary(dry17) and
  dry17['repair_write_plan']['bytes_to_write'] == 0)

# ---------------------------------------------------------------------
# V12: a zero-filled file (what a drive drop leaves) is read in bounded
# memory, in the dry run, the scan and the repair copy
# ---------------------------------------------------------------------
import tracemalloc                                          # noqa: E402
d18 = os.path.join(WORK, 'zeros')
mp18 = SY.synth_run(d18, n_depth=3000, cid='zerocid', session='20260916')
man18 = orphan(d18, mp18, rename_partial=AD.STREAMS)
zq = os.path.join(d18, man18['quotes']['file'] + '.partial')   # header + rows, then 40 MB of zeros
with open(zq, 'ab') as fh:
    for _ in range(40):
        fh.write(b'\x00' * (1 << 20))
zt = os.path.join(d18, man18['trades']['file'] + '.partial')   # zeros only, no header at all
with open(zt, 'wb') as fh:
    for _ in range(40):
        fh.write(b'\x00' * (1 << 20))
age(d18)
tracemalloc.start()
sc18 = RC.scan_stream(zq, 'quotes')
pr18 = RC.probe_stream(zt, 'trades')
_, peak18 = tracemalloc.get_traced_memory()
tracemalloc.stop()
dry18 = RC.recover_directory(d18, dry_run=True, probe=FREE)['results'][0]
rr18 = RC.recover_directory(d18, repair=True, probe=FREE)['results'][0]
t('V12: a file that turned to zeros when the drive dropped -- no line '
  'break for 40 MB -- is read in bounded memory (peak under 8 MB, not the '
  'file\'s size): the scan keeps the good rows and names the stretch as '
  'not-a-row, a header-less one has no usable rows, the dry run and the '
  'repair both say so, and nothing is written',
  sc18.rows > 0 and sc18.bad_row is not None and 'not a stream row' in sc18.bad_row[1]
  and pr18['ok'] is False and pr18.get('rows_hint') == 0 and
  peak18 < 8 * (1 << 20) and
  dry18['status'] == 'SKIPPED_NO_USABLE_ROWS' and 'trades' in dry18['empty_streams'] and
  rr18['status'] == 'SKIPPED_NO_USABLE_ROWS' and
  not any('RECOVERED' in x for x in os.listdir(d18)))

d19 = os.path.join(WORK, 'zerotail')
mp19 = SY.synth_run(d19, n_depth=3000, cid='ztailcid', session='20260917')
man19 = orphan(d19, mp19, rename_partial=AD.STREAMS)
zd = os.path.join(d19, man19['depth']['file'] + '.partial')
good19 = open(zd, 'rb').read()
with open(zd, 'ab') as fh:
    fh.write(b'\x00' * (3 << 20))                         # rows, then 3 MB of zeros
age(d19)
rr19 = RC.recover_directory(d19, repair=True, probe=FREE)['results'][0]
rec19 = [x for x in os.listdir(d19) if x.endswith('_RECOVERED.csv') and 'depth' in x][0]
t('V12b: rows followed by a zero-filled stretch: --repair keeps every '
  'good row, cuts at the stretch, and the recovered copy holds no zero '
  'byte; the original is untouched',
  rr19['status'] == 'RECONSTRUCTED' and
  b'\x00' not in open(os.path.join(d19, rec19), 'rb').read() and
  open(zd, 'rb').read()[:len(good19)] == good19 and
  os.path.getsize(os.path.join(d19, rec19)) <= len(good19))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
