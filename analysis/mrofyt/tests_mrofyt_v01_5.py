#!/usr/bin/env python3
# MROF-YT-OF-01.5 adversarial suite: the six coordinator repairs (F),
# full-lineage immutability (23 pinned hashes) and the import-graph
# proof that no executable path reaches a superseded coordinator.
# Synthetic events verify CODE BEHAVIOR only, never market evidence.
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


# ---- full-lineage immutability (v01 .. v01.4) -----------------------
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
    'MROF_YT_OF01_4_SUCCESSOR_FREEZE.md':
        'cfc27554cf1a889adde8f9be6f924d32d6902889db23eddd1c8fe9a8d765d020',
    'mrofyt_engine_v014.py':
        '8f80458add811d1799d31f061b91c585755c102f32854ce58f77678195b81a2d',
    'tests_mrofyt_v01_4.py':
        'd71e919549e8537d10e42cbc492206bf3a1ee4f8602e703204a27c14f4ba11c0',
    'REVIEW_PACKAGE_MANIFEST.md':
        'd3b4ad26b97ca20a3ccbdd93260dfbb26396ba25d14aeb5eb3b169e5ca233df1',
}
t('lineage f99c521..8cdacfd immutable (%d pinned hashes)' % len(PINNED),
  all(sha(os.path.join(HERE, fn)) == w for fn, w in PINNED.items()))
t('predecessor recorder MLES-CAPTURE-1.0.0 untouched (Freeze A)',
  sha(os.path.join(ROOT, 'src', 'MlesV1CaptureHost.cs')) ==
  'dab3abec22e16255cd27d198200125c5cd6a44192e7ff07d53ce798c755dd63d')

import mrofyt_engine_v015 as E5   # noqa: E402

LEV = {'YH': 100.0, 'PP2': 101.4}
FAM = {'YH': 'YDAY_RANGE', 'PP2': 'PIVOT'}


def deep(t0, px, n=400):
    return [(t0 + i, px, 50, px + 0.25, 50) for i in range(n)]


def eng(**kw):
    return E5.ResearchEngineV015('NQ', 'NQ 12-26', '2026-09-01', LEV,
                                 FAM, 1.0,
                                 lambda t: deep(t, 100.0), **kw)


def arrive(e, t, px=100.0):
    """Bring price into the band so the physical approach is minted at
    a PRICE event, before any signal exists."""
    e.on_price(t, px)


# =====================================================================
# F1: open-position state checked BEFORE consumed/re-arm state
# =====================================================================
e = eng()
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'f1a', 9.0)
r = e.complete_timestamp()
# same key (already consumed by the trade) fires again while in-trade
e.on_raw_callback(15.0, 'A2', +1, 100.0, 'f1b', 14.0)
e.complete_timestamp()
last = e.co.log[-1]
t('F1: a valid signal on an ALREADY-CONSUMED key while a position is '
  'open records OVERLAP_SUPPRESSED (never REARM_PENDING)',
  r is not None and last['reason'] == 'OVERLAP_SUPPRESSED')
e.on_raw_callback(16.0, 'A5', +1, 100.0, 'f1c', 15.0)
e.complete_timestamp()
t('F1b: a fresh-key signal while in-trade is also OVERLAP_SUPPRESSED',
  e.co.log[-1]['reason'] == 'OVERLAP_SUPPRESSED')
t('F1c: neither suppression opened a second position',
  len(e.co.trade_opened_records()) == 1)

# =====================================================================
# F2: an adjudicated occurrence is consumed - no stale retry
# =====================================================================
# (a) after a conflict
e = eng()
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'c_l', 9.0)
e.on_raw_callback(10.0, 'A4', -1, 100.1, 'c_s', 9.0)
e.complete_timestamp()
e.on_raw_callback(12.0, 'A2', +1, 100.0, 'c_retry', 9.5)
e.complete_timestamp()
t('F2a: after SIMULTANEOUS_DIRECTION_CONFLICT the occurrence is '
  'consumed - a stale retry is REARM_PENDING',
  e.co.log[-1]['reason'] == 'REARM_PENDING')
# (b) after risk suppression
e = eng()
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'r1', 9.0, risk_ok=False)
e.complete_timestamp()
e.on_raw_callback(11.0, 'A2', +1, 100.0, 'r2', 10.0)
e.complete_timestamp()
t('F2b: after RISK_SUPPRESSED the occurrence is consumed - immediate '
  'retry is REARM_PENDING',
  [x['reason'] for x in e.co.log] ==
  ['RISK_SUPPRESSED', 'REARM_PENDING'])
# (c) after data suppression
e = eng()
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'd1', 9.0, data_ok=False)
e.complete_timestamp()
e.on_raw_callback(11.0, 'A2', +1, 100.0, 'd2', 10.0)
e.complete_timestamp()
t('F2c: after DATA_SUPPRESSED the occurrence is consumed',
  [x['reason'] for x in e.co.log] ==
  ['DATA_SUPPRESSED', 'REARM_PENDING'])
# (d) after a missed execution
e = eng(fill_fn=lambda *a, **k: dict(filled=0.0, vwap=None,
                                     snapshot_t=None, cancelled=1.0,
                                     partial=False, missed=True))
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'm1', 9.0)
e.complete_timestamp()
e.on_raw_callback(11.0, 'A2', +1, 100.0, 'm2', 10.0)
e.complete_timestamp()
t('F2d: after EXECUTION_MISSED the occurrence is consumed',
  [x['reason'] for x in e.co.log] ==
  ['EXECUTION_MISSED', 'REARM_PENDING'])
# (e) a genuine causal reset + later-formed conditions DOES re-admit
# (fresh engine with real fills - the stub above can only ever miss)
e3 = eng()
arrive(e3, 1.0)
e3.on_raw_callback(10.0, 'A2', +1, 100.0, 'q1', 9.0, risk_ok=False)
e3.complete_timestamp()          # consumed by RISK_SUPPRESSED
e3.on_price(20.0, 103.0)         # leaves the band (reset begins)
e3.on_price(30.0, 100.1)         # re-enters (reset completes)
e3.on_raw_callback(31.0, 'A2', +1, 100.0, 'q2', 25.0)
r = e3.complete_timestamp()
t('F2e: a causal reset + conditions formed AFTER it re-admits the '
  'setup', r is not None and r['approach'] == 2)
e2 = eng()
arrive(e2, 1.0)
e2.on_raw_callback(10.0, 'A2', +1, 100.0, 's1', 9.0, risk_ok=False)
e2.complete_timestamp()
e2.on_price(20.0, 103.0)
e2.on_price(30.0, 100.1)
e2.on_raw_callback(31.0, 'A2', +1, 100.0, 's2', 5.0)   # stale
e2.complete_timestamp()
t('F2f: after a reset, conditions formed BEFORE it are still refused',
  e2.co.log[-1]['reason'] == 'DATA_SUPPRESSED')

# =====================================================================
# F3: approach IDs minted at the price event
# =====================================================================
e = eng()
e.on_price(1.0, 100.0)
at = round(100.0 / E5.TICK)
t('F3: entering the band at a PRICE event mints approach 1 before any '
  'signal exists',
  e.co._appr[at]['n'] == 1 and e.co._appr[at]['minted'] == 'PRICE_EVENT')
e.on_price(2.0, 105.0)
e.on_price(3.0, 100.2)
t('F3b: leaving and re-entering the band mints approach 2 at the '
  'price event', e.co._appr[at]['n'] == 2)
e.on_raw_callback(4.0, 'A2', +1, 100.0, 'p1', 3.5)
r = e.complete_timestamp()
t('F3c: the episode inherits the price-minted approach ordinal',
  r['approach'] == 2 and r['approach_minted'] == 'PRICE_EVENT')
e_nb = eng()
e_nb.on_raw_callback(4.0, 'A2', +1, 100.0, 'nb', 3.0)
r_nb = e_nb.complete_timestamp()
t('F3d: with no price event ever seen the fallback minting is '
  'explicitly labelled',
  r_nb['approach_minted'] == 'SIGNAL_FALLBACK')

# =====================================================================
# F4: union of level IDs, level families and signal families
# =====================================================================
e = eng()
arrive(e, 1.0)
e.on_price(1.5, 101.4)            # both level bands touched
e.on_raw_callback(10.0, 'A5', +1, 101.4, 'u2', 9.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'u1', 9.0)
r = e.complete_timestamp()
t('F4: agreeing group preserves the UNION of level IDs, level '
  'families and signal families',
  r['level_ids'] == ['PP2', 'YH'] and
  r['level_families'] == ['PIVOT', 'YDAY_RANGE'] and
  r['tagged_families'] == ['A2', 'A5'] and
  sorted(r['tagged']) == ['u1', 'u2'] and r['family'] == 'A2')

# =====================================================================
# F5: buffering — a same-time price callback must not flush
# =====================================================================
e = eng()
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'b_l', 9.0)
e.on_raw_callback(10.0, 'A4', -1, 100.1, 'b_s', 9.0)
e.on_price(10.0, 100.05)          # SAME timestamp
t('F5: a same-time price callback does NOT flush the pending group',
  e.buf.pending_t() == 10.0 and
  not any(x['reason'] == 'SIMULTANEOUS_DIRECTION_CONFLICT'
          for x in e.co.log))
e.on_price(10.5, 100.05)          # time advances -> flush
t('F5b: the group adjudicates only once event time strictly advances',
  e.buf.pending_t() is None and
  sum(1 for x in e.co.log
      if x['reason'] == 'SIMULTANEOUS_DIRECTION_CONFLICT') == 2)
e = eng()
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'x1', 9.0)
e.on_raw_callback(10.0, 'A4', -1, 100.1, 'x2', 9.0)
e.complete_timestamp()
t('F5c: an explicit timestamp-completion event also adjudicates',
  sum(1 for x in e.co.log
      if x['reason'] == 'SIMULTANEOUS_DIRECTION_CONFLICT') == 2)
e = eng()
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'y1', 9.0)
e.on_raw_callback(11.0, 'A5', +1, 100.0, 'y2', 10.0)
t('F5d: a strictly later submission releases the earlier group first',
  len(e.co.trade_opened_records()) == 1 and
  e.co.trade_opened_records()[0]['t'] == 10.0)

# =====================================================================
# F6: conflicts -> zero fill, zero position, no TRADE_OPENED
# =====================================================================
e = eng()
arrive(e, 1.0)
e.on_raw_callback(10.0, 'A2', +1, 100.0, 'z1', 9.0)
e.on_raw_callback(10.0, 'A4', -1, 100.1, 'z2', 9.0)
e.complete_timestamp()
led = e.ledger()
t('F6: opposing group -> zero filled qty, zero position, NO '
  'TRADE_OPENED record, both occurrences ledgered',
  e.co.position is None and e.co.trade_opened_records() == [] and
  all(v['filled'] == 0.0 for v in led.values()) and
  len([v for v in led.values()
       if v['reason'] == 'SIMULTANEOUS_DIRECTION_CONFLICT']) == 2 and
  all(v['id'].startswith('SE|MROF-YT-OF-01.5|NQ|NQ 12-26|')
      for v in led.values()))

# =====================================================================
# F7: wiring + import graph + uncapped policy preserved
# =====================================================================
e = eng()
ids = []
tt = 10.0
for k in range(4):
    e.on_price(tt - 1, 100.0)                  # enter band (approach k+1)
    e.on_raw_callback(tt, 'A2', +1, 100.0, 'w%d' % k, tt - 0.5)
    r = e.complete_timestamp()
    ids.append(r['approach'])
    e.on_exit(r['id'], tt + 20, 101.0)
    e.on_price(tt + 30, 103.0)                 # exit band -> reset begins
    tt += 100
t('F7: end-to-end through the wired entrypoint - four sequential '
  'independent setups produce FOUR trades (uncapped policy intact)',
  len(e.co.trade_opened_records()) == 4 and ids == [1, 2, 3, 4])

SUPERSEDED = ('mrofyt_coordinator', 'mrofyt_coordinator_v013',
              'mrofyt_engine_v014')
ALLOWED = {'tests_mrofyt_v01_2.py', 'tests_mrofyt_v01_3.py',
           'tests_mrofyt_v01_4.py', 'tests_mrofyt_v01_5.py',
           'mrofyt_coordinator.py', 'mrofyt_coordinator_v013.py',
           'mrofyt_engine_v014.py'}
violators = []
for fn in sorted(os.listdir(HERE)):
    if not fn.endswith('.py') or fn in ALLOWED:
        continue
    src = open(os.path.join(HERE, fn)).read()
    for mod in SUPERSEDED:
        if re.search(r'^\s*import %s\b' % mod, src, re.M) or \
                re.search(r'^\s*from %s\b' % mod, src, re.M):
            violators.append((fn, mod))
t('F7b: NO executable path imports a superseded coordinator '
  '(v01.2/v01.3/v01.4) - regression tests only', violators == [])
t('F7c: v01.5 declares itself the executable entrypoint',
  E5.EXECUTABLE_ENTRYPOINT is True and
  hasattr(E5, 'ResearchEngineV015'))
src5 = open(os.path.join(HERE, 'mrofyt_engine_v015.py')).read()
t('F7d: no trade-count cap exists in the v01.5 coordinator',
  'max_trades' not in src5 and 'daily_cap' not in src5 and
  'weekly_cap' not in src5)
t('F7e: A1-A6 reset-type table unchanged from v01.4',
  E5.RESET_TYPES == dict(A1='RETREAT_REAPPROACH',
                         A2='RETREAT_REAPPROACH',
                         A3='BAND_EXIT_REENTER',
                         A4='RETREAT_REAPPROACH',
                         A5='BAND_EXIT_REENTER',
                         A6='BAND_EXIT_REENTER'))

# ---- recorder MLES-CAPTURE-1.1 read-only + identity proof ----------
cs = open(os.path.join(ROOT, 'src', 'MlesV11CaptureHost.cs')).read()
code = '\n'.join(ln.split('//')[0] for ln in cs.split('\n'))
t('A/B: MLES-CAPTURE-1.1 recorder has ZERO order-API calls in code',
  re.findall(r'(SubmitOrder|ChangeOrder|CancelOrder|Account\.|'
             r'EnterLong|EnterShort|ExitLong|ExitShort)', code) == [])
for token in ('Interlocked.Increment(ref eventSeq)', 'segId', 'runId',
              '.csv.partial', 'collision-', 'FileMode.CreateNew',
              'queueOverflows', 'depthBid', 'depthAdd'):
    t('recorder 1.1 implements %r' % token, token in cs)

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
