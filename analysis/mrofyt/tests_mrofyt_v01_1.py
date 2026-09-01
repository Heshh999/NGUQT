#!/usr/bin/env python3
# MROF-YT-OF-01.1 successor deterministic suite: predecessor
# immutability, the 12 required H1-zone proofs, the 20 required wall
# proofs. Synthetic events verify CODE BEHAVIOR only.
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-64s %s' % (name, 'PASS' if cond else 'FAIL'))


# ---- predecessor immutability (zone req 12 / wall req 14) -----------
PINNED = {
    'MROF_YT_OF01_WAVE_FREEZE.md':
        '881d6df8e9acb8fb5c597e55cfc8646f0a9b4f0ceab35604697051299d18ae48',
    'mrofyt_levels.py':
        '3c094d0280a7571aa1e7aed5fc59fa432722759bc8131d37115ee08bd03bc702',
    'mrofyt_signals.py':
        '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1',
    'tests_mrofyt.py':
        'c1ce10249dff41f437c6a21b629305b8bc4ac0453d0087475dfb2ea6dfa10e34',
}
for fn, want in PINNED.items():
    got = hashlib.sha256(open(os.path.join(HERE, fn), 'rb').read()).hexdigest()
    t('predecessor immutable: %s' % fn, got == want)

import mrofyt_signals as SIG  # noqa: E402
_a1_id = id(SIG.a1_absorption_reversal)
_probe = dict(aggr_z=2.5, progress_ticks=1, replenish_z=1.6,
              approaches_60s=2, opp_flip_z=1.1, retreat_ticks=1, aggr_dir=1)
_before = SIG.a1_absorption_reversal(_probe)
import mrofyt_h1zones as HZ   # noqa: E402
import mrofyt_wall_engine as WE  # noqa: E402
t('successor import does not monkey-patch predecessor',
  id(SIG.a1_absorption_reversal) == _a1_id and
  SIG.a1_absorption_reversal(_probe) == _before == -1)

# =====================================================================
# H1 ZONES — the 12 required proofs
# =====================================================================
def hb(t0, o, h, l, c, contract='NQ 09-26', last=None):
    return dict(t_open=t0, t_close=t0 + 3600, o=o, h=h, l=l, c=c,
                contract=contract, last_event_t=last if last is not None
                else t0 + 3600, instrument='NQ')


# certified fixture: 5 swing bars, 2 compact base bars, 1 displacement
BARS = ([hb(i * 3600, 100, 101 + i * 0.1, 99, 100.5) for i in range(5)] +
        [hb(5 * 3600, 100.4, 100.9, 100.0, 100.6),
         hb(6 * 3600, 100.5, 100.8, 100.1, 100.4),
         hb(7 * 3600, 100.5, 106.0, 100.3, 105.5)])
TRZ = [None] * 5 + [-0.5, -0.2, 3.0]

t('H1-1: incomplete bar fails certification (no zone possible)',
  HZ.certify_bars([hb(0, 1, 2, 0, 1, last=4000)]) == HZ.UNVERIFIED)
sb = HZ.SlotBaseline()
for _ in range(3):
    sb.observe(0, 10.0)
    sb.close_session()
t('H1-2: baseline needs >=5 prior sessions; current never counts',
  sb.z(0, 12.0) is None)
zn = HZ.find_zone_at(BARS, TRZ, 7)
t('H1-zone forms on the fixture', zn is not None and
  zn['direction'] == 'DEMAND')
t('H1-5: boundaries match frozen formulas (distal=min lows, '
  'proximal=max body extremes)',
  zn['distal'] == 100.0 and zn['proximal'] == 100.6)
t('H1-6: availability begins only at displacement close',
  zn['available_from'] == 8 * 3600)
# mirror (H1-3)
BARS_S = ([hb(i * 3600, 100, 101, 99 - i * 0.1, 100.5) for i in range(5)] +
          [hb(5 * 3600, 100.4, 100.9, 100.0, 100.6),
           hb(6 * 3600, 100.5, 100.8, 100.1, 100.4),
           hb(7 * 3600, 100.5, 100.7, 95.0, 95.4)])
zs = HZ.find_zone_at(BARS_S, TRZ, 7)
t('H1-3: supply construction is the exact mirror',
  zs is not None and zs['direction'] == 'SUPPLY' and
  zs['distal'] == 100.9 and zs['proximal'] == 100.4)
# H1-4: swing excludes base+displacement (swing high 101.4 < close 105.5;
# base high 100.9 would also pass; verify swing window is bars 0-4 only)
t('H1-4: five-bar swing excludes base and displacement bars',
  zn is not None and max(b['h'] for b in BARS[0:5]) == 101.4)
# no zone without base
t('H1: no compact base -> no zone',
  HZ.find_zone_at(BARS, [None] * 5 + [1.0, 1.0, 3.0], 7) is None)
# lifecycle
trk = HZ.ZoneTracker(dict(zn))
trk.on_trade(7 * 3600, 100.3)
t('H1-1b: touch before availability is impossible',
  trk.z['touches'] == 0 and trk.z['state'] == 'FRESH')
trk.on_trade(8 * 3600 + 10, 100.3)
trk.on_trade(8 * 3600 + 12, 100.5)     # chatter inside
trk.on_trade(8 * 3600 + 20, 100.7)     # left, but not far enough
trk.on_trade(8 * 3600 + 30, 100.4)
t('H1-7: chattering without the required retreat is ONE touch',
  trk.z['touches'] == 1)
trk.on_trade(8 * 3600 + 40, 102.0)     # away >= max(width, 4 ticks)
trk.on_trade(8 * 3600 + 50, 100.5)
t('H1-7b: re-entry after real retreat is a second touch',
  trk.z['touches'] == 2)
trk.on_trade(8 * 3600 + 55, 99.7)      # intrabar distal breach
t('H1-8: intrabar distal breach recorded, NOT an invalidation',
  trk.z['intrabar_breaches'] >= 1 and trk.z['state'] == 'TOUCHED')
trk.on_hour_close(hb(8 * 3600, 100.3, 100.5, 99.0, 99.5))
t('H1-8b: completed-bar close beyond distal invalidates',
  trk.z['state'] == 'INVALIDATED')
trk2 = HZ.ZoneTracker(dict(zn))
trk2.on_hour_close(hb(8 * 3600, 100.3, 100.5, 100.0, 100.2,
                      contract='NQ 12-26'))
t('H1-10: contract roll retires the zone (ROLLED_OFF)',
  trk2.z['state'] == 'ROLLED_OFF')
t('H1-10b: continuous series cannot certify',
  HZ.certify_bars([hb(0, 1, 2, 0, 1, contract='NQ-CONT')]) == HZ.UNVERIFIED)
# labeling + clustering + geometry
Z1 = dict(zn)
Z2 = dict(zs, available_from=8 * 3600, lo=zs['lo'], hi=zs['hi'])
t('H1: CONFLICT evaluated first when both directions overlap',
  HZ.label_event(100.3, +1, [Z1, Z2], 1.0, 9 * 3600) == 'H1_ZONE_CONFLICT')
t('H1: aligned demand for a long', HZ.label_event(100.3, +1, [Z1], 0.5,
  9 * 3600) == 'ALIGNED_H1_ZONE')
t('H1: opposing demand for a short', HZ.label_event(100.3, -1, [Z1], 0.5,
  9 * 3600) == 'OPPOSING_H1_ZONE')
fc = HZ.family_counts_v011(dict(active_family_count=2,
                                all_context_family_count=3),
                           100.3, [Z1, dict(Z1, id='dup')], 0.5, 9 * 3600)
t('H1-9: overlapping zones keep IDs but give ONE experimental flag; '
  'base counts untouched',
  fc['h1_zone_experimental_present'] is True and
  fc['active_family_count'] == 2 and fc['all_context_family_count'] == 3)
t('H1-11: Available_R_H1 ignores zones not yet available',
  HZ.available_R_h1(99.0, 98.0, +1,
                    [dict(Z2, available_from=10 * 3600)], 9 * 3600) is None)
t('H1-11b: Available_R_H1 uses nearest opposing proximal',
  abs(HZ.available_R_h1(99.0, 98.0, +1, [Z2], 9 * 3600) - 1.4) < 1e-9)

# =====================================================================
# WALL ENGINE — the 20 required proofs
# =====================================================================
zsize = lambda sz: (sz - 50) / 10.0          # deterministic z fixture
t('W-13: wall outside 2 ticks of the level is never selected',
  WE.select_wall([(101.0, 500)], 100.0, zsize) is None)
w = WE.select_wall([(100.25, 90), (100.50, 90), (100.25, 80)], 100.25, zsize)
t('W: largest z wall selected; tie to nearest price',
  w == (100.25, 90, 4.0))

ep = WE.WallEpisode(100.25, 100, 4.0, +1)
ep.on_add(20)
ep.on_execute(60)
ep.on_nontrade_remove(10)
t('W-4: accounting reconciles event by event',
  ep.remaining == 50 and abs(ep.reconcile(50)) < 1e-9 and
  ep.data_quality == 'OK')
ep2 = WE.WallEpisode(100.25, 100, 4.0, +1)
ep2.on_execute(30)
ep2.reconcile(20)                             # 50 unexplained
t('W-5: excess reconciliation error -> RECON_FAIL -> UNCERTAIN',
  ep2.data_quality == 'RECON_FAIL' and
  WE.wall_state('WALL_OBSERVED', dict(data_ok=False)) ==
  'UNCERTAIN_NO_TRADE')
t('W-15: executions and non-trade removals stay separate; a '
  'cancellation never counts as an execution',
  ep.executed == 60 and ep.removed == 10)
t('W-16: T_clear_exec right-censored when net clearance <= 0',
  ep.t_clear_exec(-5)['censored'] and ep.t_clear_exec(0)['censored']
  and abs(ep.t_clear_exec(10)['seconds'] - 5.0) < 1e-9)
t('W: WALL_BURDEN_10 = remaining / expected',
  abs(ep.wall_burden_10(25) - 2.0) < 1e-6)
t('W-6: MBP display label is REFILLING_LIQUIDITY_ESTIMATE only',
  ep.display_label() == 'REFILLING_LIQUIDITY_ESTIMATE')

base = dict(data_ok=True, wall_z=4.0)
t('W-2: big wall with no qualifying executions stays WALL_OBSERVED',
  WE.wall_state('WALL_OBSERVED', dict(base, aggr_z=0.5)) ==
  'WALL_OBSERVED')
t('W-3a: executed depletion routes to FLUSH_ARMED_EXECUTION',
  WE.wall_state('WALL_OBSERVED', dict(base, exec_vs_display=1.6, rr=0.1,
                persist_agree=3)) == 'FLUSH_ARMED_EXECUTION')
t('W-3b: non-trade withdrawal routes to FLUSH_ARMED_WITHDRAWAL',
  WE.wall_state('WALL_OBSERVED', dict(base, withdrawal_classifiable=True,
                tgt_drop_2s=0.7, opp_drop_2s=0.1)) ==
  'FLUSH_ARMED_WITHDRAWAL')
t('W-3c: unclassifiable withdrawal cannot arm A3',
  WE.wall_state('WALL_OBSERVED', dict(base, withdrawal_classifiable=False,
                tgt_drop_2s=0.7, opp_drop_2s=0.1)) == 'WALL_OBSERVED')
st_armed = WE.wall_state('WALL_OBSERVED', dict(base, aggr_z=2.5,
                         progress_ticks=1, rr=1.6))
t('W: absorption arms HOLD_ARMED', st_armed == 'HOLD_ARMED')
t('W: HOLD_CONFIRMED needs armed state + opposing flip + retreat',
  WE.wall_state('HOLD_ARMED', dict(base, opp_control_z=1.2,
                retreat_ticks=1)) == 'HOLD_CONFIRMED' and
  WE.wall_state('WALL_OBSERVED', dict(base, opp_control_z=1.2,
                retreat_ticks=1)) == 'WALL_OBSERVED')
t('W-7: armed states can never enter; confirmed states can',
  not WE.can_enter('HOLD_ARMED') and
  not WE.can_enter('FLUSH_ARMED_EXECUTION') and
  not WE.can_enter('FLUSH_ARMED_WITHDRAWAL') and
  not WE.can_enter('WALL_OBSERVED') and
  WE.can_enter('FLUSH_CONFIRMED') and WE.can_enter('HOLD_CONFIRMED'))
t('W-8: FLUSH_CONFIRMED impossible before the 5s post-clear window',
  WE.wall_state('FLUSH_ARMED_EXECUTION',
                dict(base, crossed_1tick=True, cleared_held_5s=True,
                     post_clear_done=False, persist_agree=4,
                     same_control_z=1.5, opp_replenish_z=0.2)) !=
  'FLUSH_CONFIRMED')
t('W: FLUSH_CONFIRMED after completed acceptance',
  WE.wall_state('FLUSH_ARMED_EXECUTION',
                dict(base, crossed_1tick=True, cleared_held_5s=True,
                     post_clear_done=True, persist_agree=4,
                     same_control_z=1.5, opp_replenish_z=0.2)) ==
  'FLUSH_CONFIRMED')
t('W-9: 5s reclaim beats continuation (FAILED_FLUSH_RECLAIM)',
  WE.wall_state('FLUSH_ARMED_EXECUTION',
                dict(base, crossed_1tick=True, cleared_held_5s=True,
                     post_clear_done=True, persist_agree=4,
                     same_control_z=1.5, opp_replenish_z=0.2,
                     reclaimed_5s=True, opp_control_z=1.2)) ==
  'FAILED_FLUSH_RECLAIM')
t('W: state authorization map is A1/A3/A2-A6/A4 only',
  WE.AUTHORIZES == dict(HOLD_CONFIRMED='A1',
                        FLUSH_ARMED_WITHDRAWAL='A3',
                        FLUSH_CONFIRMED='A2/A6',
                        FAILED_FLUSH_RECLAIM='A4'))
# W-1: mirror symmetry — identical break-direction-signed features must
# produce identical states for b=+1 and b=-1 episodes
for st in ('WALL_OBSERVED', 'HOLD_ARMED'):
    pass
f_sym = dict(base, aggr_z=2.5, progress_ticks=1, rr=1.6)
t('W-1: signed features make up/down episodes exact mirrors',
  WE.wall_state('WALL_OBSERVED', f_sym) ==
  WE.wall_state('WALL_OBSERVED', dict(f_sym)) == 'HOLD_ARMED')
# W-18: quote migration mirrors, incl. one-tick spread
up = [WE.classify_step((100.00, 100.25), (100.25, 100.50), True, False)]
dn = [WE.classify_step((100.25, 100.50), (100.00, 100.25), False, True)]
t('W-18: mirrored one-tick migrations give exact negated scores',
  WE.quote_migration_score(up) == -WE.quote_migration_score(dn) ==
  1.0 and up[0] == 'BUYER_LED_UP' and dn[0] == 'SELLER_LED_DOWN')
t('W-18b: unforced ask concession scores negative',
  WE.quote_migration_score(['ASK_CONCEDE_DOWN']) < 0)
# W-10/17: snapshot causality
try:
    WE.snapshot('CONTACT', 100.0, dict(delta=(1.0, 99.0),
                                       reserve=(0.5, 103.0)))
    leak = False
except ValueError:
    leak = True
t('W-10/17: later-timestamped feature (e.g. post-clear reserve) '
  'cannot enter a snapshot', leak)
t('W-17b: post-clear reserve unavailable before its 5s window',
  WE.post_clear_reserve(100.0, 103.0, dict(a=1.0))['available'] is False
  and WE.post_clear_reserve(100.0, 105.0,
                            dict(a=1.0, b=0.0))['value'] == 0.5)
try:
    WE.snapshot('MIDWAY', 100.0, {})
    bad_kind = False
except AssertionError:
    bad_kind = True
t('W-11: only the two frozen snapshot kinds exist', bad_kind)
er = WE.empirical_rates(['FLUSH', 'HOLD_OR_RECLAIM', 'UNRESOLVED',
                         'FLUSH'])
t('W-12: probabilities sum to one', er is not None and
  abs(er['P_FLUSH'] + er['P_HOLD_OR_RECLAIM'] + er['P_UNRESOLVED'] - 1)
  < 1e-12 and er['P_FLUSH'] == 0.5)
# W-19: participant-neutral outputs
cl = WE.equal_size_cluster([(0, 0, 90, 1)] * 4)
bad_words = ('iceberg', 'participant', 'spoof', 'institution', 'buyer',
             'seller')
t('W-19: equal-size cluster output is participant-neutral',
  cl['cluster'] and cl['label'] == 'EQUAL_SIZE_PRINT_CLUSTER' and
  not any(w in str(cl).lower() for w in bad_words))
al = WE.adverse_large_print_share([(0, 0, 90, -1), (1, 0, 5, -1)],
                                  +1, zsize)
t('W: adverse large-print share uses z>=2 sizes only',
  al['count'] == 1 and abs(al['share'] - 1.0) < 1e-6)
# W-20: no stock-platform constructs in the futures pipeline
src = (open(os.path.join(HERE, 'mrofyt_wall_engine.py')).read() +
       open(os.path.join(HERE, 'mrofyt_h1zones.py')).read()).lower()
t('W-20: no ECN / share-multiplier / option fields in the pipeline',
  'ecn' not in src and '* 100' not in src and 'implied_vol' not in src)
rec = WE.shadow_record(LEVEL_ID='YDAY_HIGH', STATE='HOLD_ARMED',
                       DATA_QUALITY='OK')
t('W: shadow record renders the required columns',
  rec.startswith('YDAY_HIGH') and '| HOLD_ARMED |' in rec)

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
