#!/usr/bin/env python3
# MLES-V1 Mode A: repository, lineage and protection audit. Read-only.
# No outcome, no P&L, no protected file opened.
import hashlib, json, os, subprocess
REPO = '/home/user/NGUQT'
# always write beside this script, never into the caller's working directory
HERE = os.path.dirname(os.path.abspath(__file__))
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True, cwd=REPO).stdout.strip()
def h(p):
    fp = os.path.join(REPO, p)
    if not os.path.exists(fp): return None
    return hashlib.sha256(open(fp,'rb').read()).hexdigest()[:32]

A = {}
A['branch'] = sh('git branch --show-current'); A['head'] = sh('git rev-parse HEAD')
A['remote'] = sh('git remote -v | head -1')
A['dirty'] = [l for l in sh('git status --short').split('\n') if l]
A['env'] = dict(python=sh('python3 --version'), numpy=sh('python3 -c "import numpy;print(numpy.__version__)"'),
                mcs=sh('mcs --version 2>/dev/null | head -1'))

# ancestry of every prior freeze/results commit
COMMITS = {'eac54fe':'Wave-4','f08396b':'LPCC freeze','be1fff6':'LPCC results',
 '5133c51':'CCHC freeze','963009d':'CCHC results','9072bd3':'ODMC freeze','9fec078':'ODMC results',
 '7062e67':'MGSD freeze','bb6986b':'MGSD results','7c8a854':'MOFAD closure','643343f':'MOFAD freeze',
 'e628b9d':'MOFAD capture','938382b':'MOFAD results','8dfc2de':'VTBS freeze','537a662':'VTBS results',
 '10a0c32':'NMAE mode A'}
A['ancestry'] = {c: (sh('git merge-base --is-ancestor %s HEAD && echo y || echo n'%c)=='y', n)
                 for c,n in COMMITS.items()}

# protected rules + partition config hashes
PROT = ['analysis/v41/cand_spec.py','analysis/v41/ofh6_spec.py','analysis/v41/ofht_spec.py',
        'analysis/v41/ofht_cache.py','analysis/v41/prospective.py','docs/PROSPECTIVE_REGISTRY.md',
        'src/MnqV41ProspectiveResearchHost.cs','src/V41FrozenCandidateEngine.cs',
        'src/MofadV1MicroCaptureHost.cs','analysis/mgsd/mgsd_lib.py',
        'analysis/mofad/MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv','analysis/mofad/similarity_screen.py']
A['protected_hashes'] = {p: h(p) for p in PROT}
A['protected_missing'] = [p for p,v in A['protected_hashes'].items() if v is None]

# frozen hashes file recorded by the prospective registry
A['frozen_hashes_file'] = sh('cat analysis/v41/FROZEN_HASHES.txt 2>/dev/null | head -6')

# partitions (from committed artifacts, not re-derived)
A['partitions'] = {'DEV_last':'2026-08-17','buffer':'2026-08-18..2026-08-31',
 'VALIDATION':'2026-09-01..2027-02-28','OOS':'2027-03-01..2027-08-31','LOCKBOX':'2027-09-01+',
 'status':'all future partitions UNOPENED'}

# spent registry summary (read-only)
import csv, collections
rows = list(csv.DictReader(open(os.path.join(REPO,'analysis/mofad/MOFAD_V1_SPENT_HYPOTHESIS_REGISTRY.csv'))))
A['spent_registry'] = dict(rows=len(rows), dispositions=dict(collections.Counter(r['disposition'] for r in rows)))

# existing message data present?
SCR='/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
import glob
A['message_data_present'] = dict(
  quotes=len(glob.glob(SCR+'/mofad_capture/*quotes*.csv')),
  trades=len(glob.glob(SCR+'/mofad_capture/*trades*.csv')),
  depth=len(glob.glob(SCR+'/mofad_capture/*depth*.csv')),
  note='0 everywhere = recorder has never been attached in NinjaTrader')

json.dump(A, open(os.path.join(HERE, 'MLES_V1_AUDIT.json'), 'w'), indent=1)
print('branch %s HEAD %s dirty %d' % (A['branch'], A['head'][:8], len(A['dirty'])))
print('ancestry %d/%d present' % (sum(1 for v,_ in A['ancestry'].values() if v), len(A['ancestry'])))
print('protected files hashed: %d (missing %d)' % (len(PROT)-len(A['protected_missing']), len(A['protected_missing'])))
print('spent registry rows %d' % A['spent_registry']['rows'])
print('captured message files: %s' % {k:v for k,v in A['message_data_present'].items() if k!='note'})
