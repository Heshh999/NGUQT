#!/usr/bin/env python3
# MROF-YT-OF-01.3 adversarial suite: final-prompt tests (a)-(i) plus
# the nine repair proofs and full-lineage immutability (13 hashes).
# Synthetic events verify CODE BEHAVIOR only.
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-66s %s' % (name, 'PASS' if cond else 'FAIL'))


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
}
ok_all = all(hashlib.sha256(open(os.path.join(HERE, fn), 'rb').read())
             .hexdigest() == want for fn, want in PINNED.items())
t('predecessors f99c521+0bf0ec5+3aa0f61 immutable (13 pinned hashes)',
  ok_all)
t('final prompt archived with verified hash 74ff9a99...',
  hashlib.sha256(open(os.path.join(
      HERE, 'MROF_YT_OF01_FINAL_SOURCE_PROMPT.md'), 'rb').read())
  .hexdigest() ==
  '74ff9a99e468e22326dad9e01e4ee4dc7ab90c8da7e330a6b5f9e70e9eecb91b')

import mrofyt_coordinator_v013 as C3   # noqa: E402
import mrofyt_h1zones as HZ            # noqa: E402


def deep(t0, px, n=200):
    return [(t0 + i, px, 50, px + 0.25, 50) for i in range(n)]


LEV = {'YH': 100.0, 'PPv': 200.0}
FAM = {'YH': 'YDAY_RANGE', 'PPv': 'PIVOT'}


def mkco(**kw):
    return C3.CoordinatorV013('NQ', 'NQ 09-26', '2026-09-01', LEV, FAM,
                              1.0, **kw)


def sig(family, d, px, cb, formed=None):
    return dict(family=family, direction=d, trigger_px=px,
                level_ids=[], callback_id=cb,
                formed_from_t=formed if formed is not None else 0.0)


# ---- repair 1: deterministic, callback-order-independent identity ---
co1, co2 = mkco(), mkco()
ra = co1.on_signals(10.0, [sig('A2', 1, 100.0, 'x'),
                           sig('A5', 1, 100.1, 'y')], deep(10.0, 100.0))
rb = co2.on_signals(10.0, [sig('A5', 1, 100.1, 'y'),
                           sig('A2', 1, 100.0, 'x')], deep(10.0, 100.0))
t('R1: SETUP_EPISODE_ID identical regardless of callback order',
  ra['id'] == rb['id'] and ra['id'].startswith(
      'SE|MROF-YT-OF-01.3|NQ|NQ 09-26|2026-09-01|A2|C'))
t('R1b: id carries spec/instrument/contract/session/family/cluster/'
  'approach', ra['id'].endswith('approach001'))

# ---- (a) zero valid episodes -> zero trades -------------------------
co = mkco()
t('(a) zero valid episodes create zero trades',
  co.on_signals(10.0, [sig('A2', 1, 150.0, 'z')], deep(10, 150)) is None
  and not co.trade_opened_records())

# ---- (b) four sequential independent episodes -> four trades --------
co = mkco()
ids = []
tt = 10.0
for k in range(4):
    r = co.on_signals(tt, [sig('A2', 1, 100.0, 'b%d' % k,
                               formed=tt - 1)], deep(tt, 100.0))
    ids.append(r['id'])
    co.on_exit(r['id'], tt + 30, 101.0)
    # genuine re-arm: 2-tick retreat then re-approach (A2 = wall family)
    co.on_price(tt + 40, 100.6)
    co.on_price(tt + 50, 100.1)
    tt += 100
t('(b) four sequential independent episodes -> FOUR trades (no cap, '
  'no quota)', len(co.trade_opened_records()) == 4 and
  len(set(ids)) == 4 and ids[3].endswith('approach004'))

# ---- (c) repeated callbacks + overlapping levels -> one trade -------
co = mkco()
r = co.on_signals(10.0, [sig('A2', 1, 100.0, 'c1')], deep(10, 100.0))
co.on_signals(10.0, [sig('A2', 1, 100.0, 'c1')], deep(10, 100.0))
co.on_signals(11.0, [sig('A2', 1, 100.2, 'c2', formed=0.0)],
              deep(11, 100.0))
t('(c) repeated callback and overlapping-level repeat -> ONE trade',
  len(co.trade_opened_records()) == 1 and
  co.log[-2]['reason'] == 'DUPLICATE_CALLBACK' and
  co.log[-1]['reason'] == 'REARM_PENDING')

# ---- (d) exit without frozen reset cannot re-enter ------------------
co = mkco()
r = co.on_signals(10.0, [sig('A2', 1, 100.0, 'd1')], deep(10, 100.0))
co.on_exit(r['id'], 20.0, 101.0)
r2 = co.on_signals(25.0, [sig('A2', 1, 100.0, 'd2', formed=24.0)],
                   deep(25, 100.0))
t('(d) after exit, no re-entry without the frozen reset (no time '
  'cooldown can help)', r2 is None and
  co.log[-1]['reason'] == 'REARM_PENDING')
# even 10,000 seconds later - time alone NEVER re-arms
r3 = co.on_signals(10000.0, [sig('A2', 1, 100.0, 'd3', formed=9999.0)],
                   deep(10000, 100.0))
t('(d2) elapsed time alone never re-arms (no invented cooldown)',
  r3 is None and co.log[-1]['reason'] == 'REARM_PENDING')

# ---- (e) a fully re-armed setup re-enters the same day --------------
co.on_price(10010.0, 100.6)      # >= 2-tick retreat (A2 wall family)
co.on_price(10020.0, 100.1)      # re-approach
r4 = co.on_signals(10030.0, [sig('A2', 1, 100.0, 'e1',
                                 formed=10020.0)], deep(10030, 100.0))
t('(e) re-armed by retreat/new approach -> same-day re-entry, next '
  'approach ordinal', r4 is not None and r4['id'].endswith('approach002'))
# conditions must reform from later data
co.on_exit(r4['id'], 10040.0, 101.0)
co.on_price(10050.0, 100.6)
co.on_price(10060.0, 100.1)
r5 = co.on_signals(10070.0, [sig('A2', 1, 100.0, 'e2',
                                 formed=10005.0)], deep(10070, 100.0))
t('(e2) stale conditions formed before the reset are refused',
  r5 is None and co.log[-1]['reason'] == 'REARM_PENDING')

# ---- non-wall family band-exit reset --------------------------------
co = mkco()
r = co.on_signals(10.0, [sig('A5', 1, 100.0, 'f1')], deep(10, 100.0))
co.on_exit(r['id'], 20.0, 101.0)
co.on_price(30.0, 100.9)          # still inside band (radius 1.0)
rx = co.on_signals(35.0, [sig('A5', 1, 100.0, 'f2', formed=34.0)],
                   deep(35, 100.0))
co.on_price(40.0, 101.5)          # exits proximity band
co.on_price(50.0, 100.3)          # re-enters
ry = co.on_signals(55.0, [sig('A5', 1, 100.0, 'f3', formed=52.0)],
                   deep(55, 100.0))
t('non-wall family resets ONLY via band exit + re-entry',
  rx is None and ry is not None)

# ---- (f) same-direction exact ties -> one tagged position -----------
co = mkco()
r = co.on_signals(10.0, [sig('A5', 1, 100.1, 'g2'),
                         sig('A2', 1, 100.0, 'g1'),
                         sig('A6', 1, 100.2, 'g3')], deep(10, 100.0))
t('(f) agreeing exact ties -> ONE position, lowest family ID (A2) '
  'wins, all tagged',
  r is not None and r['family'] == 'A2' and
  set(r['tagged']) == {'g1', 'g2', 'g3'} and
  r['tagged_families'] == ['A2', 'A5', 'A6'] and
  len(co.trade_opened_records()) == 1)

# ---- (g) opposite-direction exact ties: NO fill, NO TRADE_OPENED ----
co = mkco()
r = co.on_signals(10.0, [sig('A2', 1, 100.0, 'h1'),
                         sig('A4', -1, 100.1, 'h2')], deep(10, 100.0))
filled_any = any(e.get('filled', 0) > 0 for e in co.episodes.values())
t('(g) opposing exact ties -> zero filled quantity, no episode, no '
  'TRADE_OPENED record, no position',
  r is None and not co.episodes and filled_any is False and
  co.trade_opened_records() == [] and co.position is None and
  co.log[-1]['reason'] == 'SIMULTANEOUS_DIRECTION_CONFLICT')

# ---- (h) open-position signals suppressed at original time ----------
co = mkco()
r = co.on_signals(10.0, [sig('A2', 1, 100.0, 'i1')], deep(10, 100.0))
co.on_signals(15.0, [sig('A5', -1, 200.0, 'i2')], deep(15, 200.0))
sup = [x for x in co.log if x['reason'] == 'NOT_FLAT_SUPPRESSED']
co.on_exit(r['id'], 30.0, 101.0)
t('(h) open-position signal recorded at its original time (t=15) and '
  'never entered later',
  len(sup) == 1 and sup[0]['t'] == 15.0 and
  len(co.trade_opened_records()) == 1)

# ---- (i) no configurable trade-count cap exists ---------------------
src13 = open(os.path.join(HERE, 'mrofyt_coordinator_v013.py')).read()
t('(i) no daily/weekly trade-count cap exists in the coordinator '
  'source; risk gate remains functional',
  'max_trades' not in src13 and 'daily_cap' not in src13 and
  'weekly_cap' not in src13)
co = mkco()
rr = co.on_signals(10.0, [dict(sig('A2', 1, 100.0, 'j1'),
                               risk_ok=False)], deep(10, 100.0))
t('(i2) risk kill switch still suppresses (RISK_SUPPRESSED)',
  rr is None and co.log[-1]['reason'] == 'RISK_SUPPRESSED')

# ---- repair 3: no 1-ms window — nearby timestamps are DIFFERENT -----
co = mkco()
co.on_signals(10.0, [sig('A2', 1, 100.0, 'k1')], deep(10, 100.0))
co.on_signals(10.0005, [sig('A4', -1, 100.1, 'k2')], deep(10, 100.0))
t('repair3: 10.0005s after 10.0s is NOT simultaneous (no arbitrary '
  'window); it is an ordinary not-flat suppression',
  co.log[-1]['reason'] == 'NOT_FLAT_SUPPRESSED' and
  'SIMULTANEOUS' not in ' '.join(x['reason'] for x in co.log))

# ---- repair 4: display labels never change the reset key ------------
co = mkco()
co.levels['ALIAS'] = 100.0
co.family_of['ALIAS'] = 'YDAY_RANGE'
r = co.on_signals(10.0, [sig('A2', 1, 100.0, 'l1')], deep(10, 100.0))
co.on_exit(r['id'], 20.0, 101.0)
r2 = co.on_signals(25.0, [sig('A2', 1, 100.05, 'l2', formed=24.0)],
                   deep(25, 100.0))
t('repair4: an aliased display label cannot bypass the reset key',
  r2 is None and co.log[-1]['reason'] == 'REARM_PENDING')

# ---- repair 5: event-driven liquidity -------------------------------
q_rep = [(10.2, 100.0, 5, 100.25, 3), (10.4, 100.0, 5, 100.25, 3),
         (10.6, 100.0, 5, 100.25, 3)]
f = C3.fill_event_driven(q_rep, 10.0, +1, 9)
t('repair5: unchanged repeated quote is NOT new liquidity (9 requested '
  '-> only 3 filled)', f['filled'] == 3 and f['partial'])
q_rep2 = [(10.2, 100.0, 5, 100.25, 3), (10.4, 100.0, 5, 100.25, 8)]
f2 = C3.fill_event_driven(q_rep2, 10.0, +1, 9)
t('repair5b: genuine replenishment (+5) adds availability -> 8 filled',
  f2['filled'] == 8)
q_rep3 = [(10.2, 100.0, 5, 100.25, 3), (10.4, 100.0, 5, 100.50, 4)]
f3 = C3.fill_event_driven(q_rep3, 10.0, +1, 9)
t('repair5c: a new price level is new liquidity (3 + 4 = 7 filled)',
  f3['filled'] == 7 and abs(f3['vwap'] -
                            (3 * 100.25 + 4 * 100.50) / 7) < 1e-9)

# ---- repair 6: strict slot baseline + calendar-validated zones ------
sb = C3.StrictSlotBaseline(n=20)
for k in range(19):
    sb.observe(3, 10.0 + 0.1 * k)
    sb.close_session()
z19 = sb.z(3, 12.0)
sb.observe(3, 11.9)
sb.close_session()
t('repair6: H1 SlotBaseline strict (19 sessions -> None, 20 -> value)',
  z19 is None and sb.z(3, 12.0) is not None)


def hb(t0, o, h, l, c, contract='NQ 09-26'):
    return dict(t_open=t0, t_close=t0 + 3600, o=o, h=h, l=l, c=c,
                contract=contract, last_event_t=t0 + 3600,
                instrument='NQ')


BARS = ([hb(i * 3600, 100, 101 + i * 0.1, 99, 100.5) for i in range(5)] +
        [hb(5 * 3600, 100.4, 100.9, 100.0, 100.6),
         hb(6 * 3600, 100.5, 100.8, 100.1, 100.4),
         hb(7 * 3600, 100.5, 106.0, 100.3, 105.5)])
TRZ = [None] * 5 + [-0.5, -0.2, 3.0]
CAL = C3.SessionCalendar('CME-v1', [i * 3600 for i in range(9)])
t('repair6b: calendar-valid window forms the zone',
  C3.find_zone_at_v013(BARS, TRZ, 7, CAL) is not None)
CAL_H = C3.SessionCalendar('CME-v1', [i * 3600 for i in range(9)],
                           holidays=[6 * 3600])
t('repair6c: a holiday bar inside the window kills the zone',
  C3.find_zone_at_v013(BARS, TRZ, 7, CAL_H) is None)
CAL_M = C3.SessionCalendar('CME-v1', [i * 3600 for i in range(9)],
                           maintenance_hours=[2 * 3600])
t('repair6d: a maintenance-break bar inside the swing kills the zone',
  C3.find_zone_at_v013(BARS, TRZ, 7, CAL_M) is None)

# ---- repair 7: wall-episode identity + lifecycle --------------------
reg = C3.WallEpisodeRegistryV013('NQ', 'NQ 09-26', '2026-09-01')
e1, w1 = reg.open_episode('ask', 15000.0)
e2, w2 = reg.open_episode('bid', 15000.0)
t('repair7: opposite-side walls at one price NEVER merge',
  w1 == 'NEW' and w2 == 'NEW' and e1['id'] != e2['id'] and
  '|ask|' in e1['id'] and '|bid|' in e2['id'])
reg.close_episode('ask', 15000.0, 'CLOSED_FLUSH')
e3, w3 = reg.open_episode('ask', 15000.0)
t('repair7b: a later independent approach forms a NEW episode with '
  'the next ordinal', w3 == 'NEW' and e3['id'].endswith('approach02'))
try:
    reg.close_episode('bid', 15000.0, 'PROFITABLE')
    bad = False
except AssertionError:
    bad = True
t('repair7c: only frozen terminal states are accepted', bad)
t('repair7d: episode id carries instrument|contract|session|side|'
  'price|approach',
  e3['id'] == 'WE|NQ|NQ 09-26|2026-09-01|ask|15000.00|approach02')

# ---- repair 8: completed deployment/handoff docs --------------------
dep = open(os.path.join(HERE, 'RECORDER_DEPLOYMENT_v01_3.md')).read()
hnd = open(os.path.join(HERE, 'DATA_HANDOFF_v01_3.md')).read()
need_dep = ('namespace', 'F5', 'smoke test', 'health', 'Market Replay',
            'read-only', 'ten-level', 'start', 'stop')
need_hnd = ('manifest', 'SHA-256', 'copy', 'INSUFFICIENT_DATA',
            'data_root', 'parser')
t('repair8: deployment runbook covers namespace/F5/smoke/health/'
  'replay/read-only/levels/start-stop',
  all(k.lower() in dep.lower() for k in need_dep))
t('repair8b: handoff doc covers manifests/hashes/copy/data_root/'
  'parser/insufficient-data',
  all(k.lower() in hnd.lower() for k in need_hnd))

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
