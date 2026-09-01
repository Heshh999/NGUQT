#!/usr/bin/env python3
# MROF-YT-OF-01.4 adversarial suite: engine-boundary grouping, re-arm
# gating, permanent overlap consumption, causality window, first-book
# fills, approach identity, ledger completeness, reset-type dispatch,
# end-to-end wiring, import graph, and review-package verification.
import hashlib
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-66s %s' % (name, 'PASS' if cond else 'FAIL'))


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


# ---- immutability: full lineage (19 pinned hashes) ------------------
PINNED = {
    'MROF_YT_OF01_WAVE_FREEZE.md':
        '881d6df8e9acb8fb5c597e55cfc8646f0a9b4f0ceab35604697051299d18ae48',
    'mrofyt_levels.py':
        '3c094d0280a7571aa1e7aed5fc59fa432722759bc8131d37115ee08bd03bc702',
    'mrofyt_signals.py':
        '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1',
    'tests_mrofyt.py':
        'c1ce10249dff41f437c6a21b629305b8bc4ac0453d0087475dfb2ea6dfa10e34',
    'MROF_YT_OF01_1_SUCCESSOR_FREEZE.md':
        '69d1dfb228681cf4097fc8f3cc800a3ce941d5edfef9bf915cd1534f8d2102dc',
    'mrofyt_h1zones.py':
        '9ee941e28f6f12b4a1d1c9a340f37990faa9f7c10a736d94c9437513922b8186',
    'mrofyt_wall_engine.py':
        'a8ccc3dd9a14de98bf6670026933db5153fd65155d0502bc776381aced332077',
    'tests_mrofyt_v01_1.py':
        '30e858e87d7fa81fc2c5ca1466e5f3afc2d14ef3cef6a1bbda4fb41eb467e776',
    'MROF_YT_OF01_2_SUCCESSOR_FREEZE.md':
        '77a58288791e6f861da2abc3dc736352aae01ea964c434f895d3bf2baf9cb639',
    'mrofyt_coordinator.py':
        '2db5524a1a8e4877931c2ad5b578c384d76808661a9994e2d15b33a11a4a66e8',
    'tests_mrofyt_v01_2.py':
        'ea3770f5e0772d2f46a35f55c3c89d08c5b6ce831bd0c6aaaaa549c45bdb8560',
    'RECORDER_DEPLOYMENT.md':
        'cb9d3fd0d1329dda1e0f8b39974995b8dfa10254d5170c16e7c1aefb948a5a30',
    'DATA_HANDOFF.md':
        '2d7a9400ee0823bedad0183d633900f691dfb8819f4d140b0ac0cbf2ff0652b2',
    'MROF_YT_OF01_3_SUCCESSOR_FREEZE.md':
        'a7af6b33f3ab3d5e73c6b4fd5146a18180f81ede4e615ed15fb4b2b28b13bf26',
    'mrofyt_coordinator_v013.py':
        'c0fd9f04d4c17b78722e74bd48f1dd4f57a521993907818fea0d65e75941d4ef',
    'tests_mrofyt_v01_3.py':
        '788248f531afc7e56ad793fb9a9a8828cdc180d605987c7ca36ab1104a18f971',
    'RECORDER_DEPLOYMENT_v01_3.md':
        'c5b0a9023631a5f1cc21fddc868bbbc95d9ec42dd825f08b34639bfa761293f4',
    'DATA_HANDOFF_v01_3.md':
        '71bcf2f6b23aae830bbaf9e84dce7161596921342f2788c0eb8b46c613376f8d',
    'MROF_YT_OF01_FINAL_SOURCE_PROMPT.md':
        '74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b',
}
t('predecessors f99c521+0bf0ec5+3aa0f61+4f821f1 immutable (19 hashes)',
  all(sha(os.path.join(HERE, fn)) == want
      for fn, want in PINNED.items()))

import mrofyt_engine_v014 as E4   # noqa: E402


def deep(t0, px, n=200):
    return [(t0 + i, px, 50, px + 0.25, 50) for i in range(n)]


LEV = {'YH': 100.0, 'PPv': 200.0}
FAM = {'YH': 'YDAY_RANGE', 'PPv': 'PIVOT'}
QF = {'quotes': deep(0.0, 100.0, 20000)}


def eng(**kw):
    return E4.ResearchEngineV014('NQ', 'NQ 09-26', '2026-09-01', LEV,
                                 FAM, 1.0,
                                 lambda t: [q for q in QF['quotes']
                                            if q[0] > t - 1], **kw)


# =====================================================================
# requirement 1: SignalGroupBuffer at the engine boundary
# =====================================================================
e = eng()
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'cb_long', 9.0)
e.on_raw_callback(10.0, 'A4', -1, 100.1, 'cb_short', 9.0)
e.flush()
led = e.ledger()
t('req1: two SEPARATE opposing callbacks at one exact completion '
  'timestamp -> zero fills, zero positions, no TRADE_OPENED',
  e.co.position is None and e.co.trade_opened_records() == [] and
  all(v['filled'] == 0 for v in led.values()) and
  len([v for v in led.values()
       if v['reason'] == 'SIMULTANEOUS_DIRECTION_CONFLICT']) == 2)
e2 = eng()
e2.on_raw_callback(10.0, 'A5', +1, 100.1, 'g2', 9.0)
e2.on_raw_callback(10.0, 'A2', +1, 100.0, 'g1', 9.0)
r = e2.flush()
t('req1b: agreeing separate callbacks group to ONE position, lowest '
  'family wins, all tagged',
  r is not None and r['family'] == 'A2' and
  set(r['tagged']) == {'g1', 'g2'} and
  len(e2.co.trade_opened_records()) == 1)
e3 = eng()
e3.on_raw_callback(10.0, 'A2', +1, 100.0, 'w1', 9.0)
e3.on_raw_callback(12.0, 'A5', +1, 100.0, 'w2', 11.0)   # later t flushes
t('req1c: a later-timestamp submission releases the earlier group '
  'before any mixing', len(e3.co.trade_opened_records()) == 1 and
  e3.co.trade_opened_records()[0]['t'] == 10.0)

# =====================================================================
# requirement 2: re-arm tracking only after terminal + flat
# =====================================================================
e = eng()
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'q1', 9.0)
r = e.flush()
# price retreats and re-approaches WHILE the position is open
e.co.on_price(15.0, 100.6)
e.co.on_price(16.0, 100.1)
e.co.on_exit(r['id'], 20.0, 101.0)
e.on_raw_callback(25.0, 'A2', +1, 100.0, 'q2', 24.0)
e.flush()
t('req2: price movement while the position is open cannot complete '
  'the next reset',
  e.co.log[-1]['reason'] == 'REARM_PENDING')
# after flat, the SAME movement pattern re-arms
e.co.on_price(30.0, 100.6)
e.co.on_price(31.0, 100.1)
e.on_raw_callback(35.0, 'A2', +1, 100.0, 'q3', 32.0)
r2 = e.flush()
t('req2b: identical movement AFTER terminal+flat completes the reset',
  r2 is not None and r2['approach'] == 2)

# =====================================================================
# requirement 3: OVERLAP_SUPPRESSED is permanently consumed
# =====================================================================
e = eng()
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'p1', 9.0)
r = e.flush()
e.on_raw_callback(15.0, 'A5', +1, 100.0, 'p2', 14.0)
e.flush()
sup = [v for v in e.ledger().values()
       if v['reason'] == 'OVERLAP_SUPPRESSED']
t('req3: signal while another position is open -> OVERLAP_SUPPRESSED '
  'with a retained episode ID',
  len(sup) == 1 and sup[0]['id'].startswith('SE|MROF-YT-OF-01.4'))
e.co.on_exit(r['id'], 20.0, 101.0)
e.on_raw_callback(25.0, 'A5', +1, 100.0, 'p3', 24.0)
e.flush()
t('req3b: recomputing it after exit cannot enter without a genuine '
  'reset', e.co.log[-1]['reason'] == 'REARM_PENDING')
e.co.on_price(30.0, 101.5)      # A5 = band exit
e.co.on_price(31.0, 100.3)      # re-entry -> new approach
e.on_raw_callback(35.0, 'A5', +1, 100.0, 'p4', 32.0)
r2 = e.flush()
t('req3c: genuinely new reset + later-formed conditions + NEW '
  'approach ID enters', r2 is not None and r2['approach'] == 2)

# =====================================================================
# requirement 4: reset_t < formed_from_t <= signal_t
# =====================================================================
e = eng()
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'c1', 11.0)   # future-formed
e.flush()
t('req4: future-formed features -> CAUSALITY_FAILURE',
  e.co.log[-1]['reason'] == 'CAUSALITY_FAILURE')
e = eng()
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'c2', 9.0)
r = e.flush()
e.co.on_exit(r['id'], 20.0, 101.0)
e.co.on_price(30.0, 100.6)       # reset_t = 30.0 (retreat start)
e.co.on_price(31.0, 100.1)
e.on_raw_callback(35.0, 'A2', +1, 100.0, 'c3', 30.0)   # == reset_t
e.flush()
t('req4b: formed_from_t EQUAL to the reset timestamp is rejected '
  '(DATA_SUPPRESSED)', e.co.log[-1]['reason'] == 'DATA_SUPPRESSED')
e.on_raw_callback(36.0, 'A2', +1, 100.0, 'c4', 29.0)   # stale
e.flush()
t('req4c: stale (pre-reset) features rejected',
  e.co.log[-1]['reason'] == 'DATA_SUPPRESSED')
e.on_raw_callback(37.0, 'A2', +1, 100.0, 'c5', 30.5)   # strictly inside
r2 = e.flush()
t('req4d: reset_t < formed_from_t <= signal_t admits the signal',
  r2 is not None)

# =====================================================================
# requirement 5: first-executable-book fills
# =====================================================================
qthin = [(10.2, 100.0, 5, 100.25, 3), (10.4, 100.0, 5, 100.25, 50),
         (11.0, 100.0, 5, 100.25, 50)]
f = E4.fill_first_book(qthin, 10.0, +1, 5)
t('req5: fill ONLY against the first valid snapshot; remainder '
  'cancelled (3 filled, 2 cancelled)',
  f['filled'] == 3 and f['cancelled'] == 2 and f['partial'] and
  f['snapshot_t'] == 10.2)
f2 = E4.fill_first_book([(10.0 + 7200, 100.0, 50, 100.25, 50)],
                        10.0, +1, 1)
t('req5b: a quote hours later can NEVER fill the old signal (missed)',
  f2['missed'] and f2['cancelled'] == 1)

# =====================================================================
# requirement 6: approach ID exists at approach begin, and every
# outcome type carries an episode ID
# =====================================================================
e = eng()
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'a1', 9.0)
r = e.flush()
e.co.on_exit(r['id'], 20.0, 101.0)
e.co.on_price(30.0, 100.6)
e.co.on_price(31.0, 100.1)       # approach 2 begins HERE, pre-fill
key = list(e.co._key)[0]
t('req6: the new approach ID exists at the price event, before any '
  'fill attempt', e.co._key[key]['approach_n'] == 2 and
  e.co._key[key]['approach_open'])
e = eng()
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'b1', 9.0,
                  risk_ok=False)
e.on_raw_callback(10.0, 'A5', +1, 100.0, 'b2', 9.0,
                  data_ok=False)
e.flush()
e.on_raw_callback(12.0, 'A2', +1, 100.0, 'b3', 11.0)
e.co.fill_fn = lambda *a, **k: dict(filled=0.0, vwap=None,
                                    snapshot_t=None, cancelled=1.0,
                                    partial=False, missed=True)
e.flush()
led = e.ledger()
kinds = sorted(v['reason'] for v in led.values())
t('req6b: risk/data suppressions and misses ALL carry episode IDs',
  kinds == ['DATA_SUPPRESSED', 'EXECUTION_MISSED', 'RISK_SUPPRESSED']
  and all(v['id'].startswith('SE|') for v in led.values()))

# =====================================================================
# requirement 7: ledger completeness
# =====================================================================
e = eng()
e.on_raw_callback(10.0, 'A5', +1, 100.1, 'd2', 9.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'd1', 9.0)
r = e.flush()
rec = e.ledger()[r['id']]
t('req7: ledger persists level IDs, level families, agreeing signal '
  'families, contract, session, cluster and reason',
  rec['level_ids'] == ['YH'] and
  rec['level_families'] == ['YDAY_RANGE'] and
  rec['tagged_families'] == ['A2', 'A5'] and
  rec['contract'] == 'NQ 09-26' and rec['session'] == '2026-09-01' and
  rec['cluster'].startswith('C') and rec['reason'] == 'TRADE_OPENED')

# =====================================================================
# requirement 8: reset behavior from the frozen type table
# =====================================================================
e = eng(reset_types={'X1': 'RETREAT_REAPPROACH'})
e.on_raw_callback(10.0, 'X1', +1, 100.0, 'x1', 9.0)
r = e.flush()
e.co.on_exit(r['id'], 20.0, 101.0)
e.co.on_price(30.0, 100.6)       # 2-tick retreat (still inside band)
e.co.on_price(31.0, 100.1)
e.on_raw_callback(35.0, 'X1', +1, 100.0, 'x2', 32.0)
r2 = e.flush()
t('req8: a custom family with RETREAT_REAPPROACH resets via retreat '
  '(table-driven, not a hardcoded A-list)', r2 is not None)
e = eng(reset_types={'X1': 'BAND_EXIT_REENTER'})
e.on_raw_callback(10.0, 'X1', +1, 100.0, 'y1', 9.0)
r = e.flush()
e.co.on_exit(r['id'], 20.0, 101.0)
e.co.on_price(30.0, 100.6)
e.co.on_price(31.0, 100.1)       # retreat is NOT enough for band type
e.on_raw_callback(35.0, 'X1', +1, 100.0, 'y2', 32.0)
r2 = e.flush()
t('req8b: the SAME family under BAND_EXIT_REENTER refuses the '
  'retreat-only pattern', r2 is None and
  e.co.log[-1]['reason'] == 'REARM_PENDING')
t('req8c: frozen table maps A1/A2/A4 retreat, A3/A5/A6 band',
  E4.RESET_TYPES == dict(A1='RETREAT_REAPPROACH',
                         A2='RETREAT_REAPPROACH',
                         A3='BAND_EXIT_REENTER',
                         A4='RETREAT_REAPPROACH',
                         A5='BAND_EXIT_REENTER',
                         A6='BAND_EXIT_REENTER'))

# =====================================================================
# requirement 9: end-to-end wiring + import graph
# =====================================================================
e = eng()
for k in range(4):
    tt = 10.0 + 100 * k
    e.on_raw_callback(tt, 'A2', +1, 100.0, 'e%d' % k, tt - 1)
    r = e.flush()
    e.co.on_exit(r['id'], tt + 20, 101.0)
    e.co.on_price(tt + 30, 100.6)
    e.co.on_price(tt + 40, 100.1)
led = e.ledger()
t('req9: end-to-end raw callbacks -> grouping -> coordinator -> fill '
  '-> ledger; four sequential setups -> four trades (uncapped)',
  len(e.co.trade_opened_records()) == 4 and
  sorted(v['approach'] for v in led.values()) == [1, 2, 3, 4])
allowed_importers = {'tests_mrofyt_v01_2.py', 'tests_mrofyt_v01_3.py',
                     'mrofyt_coordinator.py', 'mrofyt_coordinator_v013.py'}
violators = []
for fn in os.listdir(HERE):
    if not fn.endswith('.py') or fn in allowed_importers:
        continue
    src = open(os.path.join(HERE, fn)).read()
    if re.search(r'^\s*import mrofyt_coordinator', src, re.M):
        violators.append(fn)
t('req9b: no executable path imports the superseded v01.2/v01.3 '
  'coordinators (regression tests only)', violators == [])

# =====================================================================
# requirement 10: review package independently verifiable
# =====================================================================
man = open(os.path.join(HERE, 'REVIEW_PACKAGE_MANIFEST.md')).read()
pairs = re.findall(r'^([0-9a-f]{64})\s+(\S+)$', man, re.M)
ok_pkg = True
for want, rel in pairs:
    if 'MROF_V1_Engine.zip' in rel:
        continue                       # delivered artifact, hash recorded
    p = os.path.join(ROOT, rel)
    ok_pkg = ok_pkg and os.path.exists(p) and sha(p) == want
t('req10: review-package manifest hashes match the repo files '
  '(recorder .cs, engine, integrity, closure suites)', ok_pkg)
cs_code = '\n'.join(
    ln.split('//')[0] for ln in
    open(os.path.join(ROOT, 'src', 'MlesV1CaptureHost.cs')))
api = re.findall(r'(SubmitOrder|ChangeOrder|CancelOrder|Account\.|'
                 r'EnterLong|EnterShort|ExitLong|ExitShort)', cs_code)
t('req10b: read-only recorder proof — zero order-API calls in CODE '
  '(the sole grep hit is the comment documenting the prohibition)',
  api == [])

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
