#!/usr/bin/env python3
# MROF-YT-RECOVER-1.0 suite. Manifest reconstruction for runs whose
# recorder died before finalizing. Exercised on synthetic recorder-format
# runs (mles_v12_synth) damaged in the specific ways a power loss causes.
# Synthetic events verify CODE BEHAVIOR only, never market evidence.
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_adapter as AD     # noqa: E402
import mles_v12_audit as AU       # noqa: E402
import mles_v12_synth as SY       # noqa: E402
import mrofyt_recover as RC       # noqa: E402
import mrofyt_runner as RN        # noqa: E402

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


def orphan(d, mp, rename_partial=()):
    """Delete the manifest (what an ungraceful death leaves behind) and
    optionally put some streams back into .partial form."""
    man = json.load(open(mp))
    os.remove(mp)
    for k in rename_partial:
        p = os.path.join(d, man[k]['file'])
        os.rename(p, p + '.partial')
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

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
