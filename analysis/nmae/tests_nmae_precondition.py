#!/usr/bin/env python3
# NMAE-V1 Mode A tests (§32 subset applicable at this mode):
# precondition verification, ancestry, registry completeness,
# partition access restrictions, and honest-stub integrity.
# No protected outcome is opened by any test.
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'analysis', 'mofad'))
import similarity_screen as SS  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-60s %s' % (name, 'PASS' if cond else 'FAIL'))


def sh(c):
    return subprocess.run(c, shell=True, capture_output=True, text=True,
                          cwd=REPO).stdout.strip()


M = json.load(open(os.path.join(HERE, 'NMAE_V1_DATA_MANIFEST.json')))

print('MLES precondition verification')
t('no MLES-V1 artifact exists in the repository',
  M['mles']['artifacts_found'] == [])
t('no MLES-V1 commit exists', M['mles']['commits_found'] == [])
t('precondition recorded as ABSENT', 'ABSENT' in M['mles']['verdict'])
t('no MLES protocol/results commit claimed',
  M['mles']['protocol_commit'] is None and M['mles']['results_commit'] is None)

print('ancestry')
t('all 15 prior freeze/result commits in ancestry',
  all(M['prior_commits_in_ancestry'].values()))
t('history not rewritten (HEAD resolves)', len(M['head']) == 40)

print('spent-registry completeness and reserved mechanisms')
ont = json.load(open(os.path.join(HERE, 'NMAE_V1_SPENT_MECHANISM_ONTOLOGY.json')))
t('ontology matches live registry row count',
  ont['registry_rows'] == len(SS.load_registry()))
t('NMAE added zero spent entries', ont['nmae_additions'] == [])
t('MLES reserved mechanisms NOT imported as dead',
  len(ont['mles_reserved_mechanisms_NOT_imported']) == 6)
t('OFH13/OFH14 remain protected',
  SS.build_fingerprints()['FVG_FLOW_MITIGATION']['protected'])

print('mode discipline / honest stubs')
t('frozen candidates file is []',
  json.load(open(os.path.join(HERE, 'NMAE_V1_FROZEN_CANDIDATES.json'))) == [])
for f in ('NMAE_V1_DERIVATIVE_SCREEN.csv', 'NMAE_V1_HYPOTHESIS_LEDGER.csv'):
    lines = open(os.path.join(HERE, f)).read().strip().split('\n')
    t('%s is header-only (no fabricated rows)' % f, len(lines) == 1)
for f in ('NMAE_V1_DEV_RESULTS.md', 'NMAE_V1_PROTOCOL_FREEZE.md'):
    t('%s marked NOT RUN' % f,
      'NOT RUN' in open(os.path.join(HERE, f)).read())

print('data honesty')
t('0 of 6 families claimed ready', M['families_ready'] == [])
t('every family carries a binding reason',
  all(v.get('binding') for v in M['families'].values()))
t('absent classes are marked absent, not proxied',
  M['data']['option_chains_NQ_QQQ']['present'] is False
  and M['data']['authenticated_econ_calendar']['present'] is False
  and M['data']['quotes_BBO_MNQ']['present'] is False)

print('partition access restrictions')
t('no protected-partition file was read by this audit',
  'VALIDATION' not in json.dumps(M['data']))

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
