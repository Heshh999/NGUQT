#!/usr/bin/env python3
# MROF-YT-OF-01.2 successor suite: predecessor immutability (both
# waves), the nine coordinator proofs, and the specification repairs.
# Synthetic events verify CODE BEHAVIOR only — never market evidence.
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-66s %s' % (name, 'PASS' if cond else 'FAIL'))


# ---- predecessor immutability (v01 AND v01.1) -----------------------
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
}
ok_all = True
for fn, want in PINNED.items():
    got = hashlib.sha256(open(os.path.join(HERE, fn), 'rb').read()).hexdigest()
    ok_all = ok_all and got == want
t('predecessors f99c521 + 0bf0ec5 immutable (8 pinned hashes)', ok_all)

import mrofyt_signals as SIG        # noqa: E402
import mrofyt_coordinator as CO     # noqa: E402
import mrofyt_wall_engine as WE     # noqa: E402


def Q(seq):
    return [(t_, b, bs, a, asz) for t_, b, bs, a, asz in seq]


def deep_quotes(t0, px, n=400, step=1.0):
    return [(t0 + i * step, px, 50, px + 0.25, 50) for i in range(n)]


def mkco(**kw):
    return CO.SetupCoordinator({'L1': 100.0, 'L2': 200.0}, 1.0, **kw)


# =====================================================================
# COORDINATOR — the nine required proofs
# =====================================================================
# C1: immutable SETUP_EPISODE_ID
co = mkco()
r = co.on_signal(10.0, 'A2', +1, 100.0, ['L1'], 'cb1',
                 deep_quotes(10.0, 100.0))
eid = r['id']
co.on_exit(eid, 20.0, 101.0)
t('C1: SETUP_EPISODE_ID immutable through the episode lifecycle',
  co.episodes[eid]['id'] == eid and eid.startswith('SE-'))

# C2 (required): four sequential independent setups -> four trades,
# no daily/weekly cap
co = mkco()
opened = []
for k in range(4):
    t0 = 10.0 + 200 * k
    rr = co.on_signal(t0, 'A2', +1, 100.0 + 5 * (k % 2) * 0, ['L1'],
                      'cb%d' % k, deep_quotes(t0, 100.0))
    if rr:
        opened.append(rr['id'])
        co.on_exit(rr['id'], t0 + 50, 101.0)
t('C2: four sequential independent setups produce FOUR trades (no cap)',
  len(opened) == 4 and len(set(opened)) == 4)

# C3: while-flat rule — a signal during an open position is suppressed
co = mkco()
r1 = co.on_signal(10.0, 'A2', +1, 100.0, ['L1'], 'a',
                  deep_quotes(10.0, 100.0))
r2 = co.on_signal(15.0, 'A1', -1, 200.0, ['L2'], 'b',
                  deep_quotes(15.0, 200.0))
t('C3: not-flat suppression while a position is open',
  r1 is not None and r2 is None and
  co.log[-1]['reason'] == 'NOT_FLAT_SUPPRESSED')
co.on_exit(r1['id'], 100.0, 101.0)
r3 = co.on_signal(200.0, 'A1', -1, 200.0, ['L2'], 'c',
                  deep_quotes(200.0, 200.0))
t('C3b: after flat, the next independent setup trades', r3 is not None)

# C4: duplicate callback suppression
co = mkco()
co.on_signal(10.0, 'A2', +1, 100.0, ['L1'], 'dup',
             deep_quotes(10.0, 100.0))
co.on_exit(co.log[-1]['detail'], 20.0, 101.0)
r = co.on_signal(300.0, 'A2', +1, 100.0, ['L1'], 'dup',
                 deep_quotes(300.0, 100.0))
t('C4: duplicate callback suppressed',
  r is None and co.log[-1]['reason'] == 'DUPLICATE_CALLBACK')

# C5: overlapping-level labels = ONE physical episode
co = mkco()
co.levels['L1B'] = 100.3
r1 = co.on_signal(10.0, 'A2', +1, 100.0, ['L1'], 'x1',
                  deep_quotes(10.0, 100.0))
r2 = co.on_signal(10.5, 'A2', +1, 100.2, ['L1B'], 'x2',
                  deep_quotes(10.5, 100.0))
t('C5: overlapping-level callback merges labels, no second episode',
  r2 is None and co.log[-1]['reason'] == 'OVERLAP_SUPPRESSED' and
  set(co.episodes[r1['id']]['level_ids']) >= {'L1', 'L1B'})

# C6: simultaneous opposite-direction conflict
co = mkco()
co.on_signal(10.0, 'A2', +1, 100.0, ['L1'], 's1',
             deep_quotes(10.0, 100.0))
r2 = co.on_signal(10.0005, 'A4', -1, 100.1, ['L1'], 's2',
                  deep_quotes(10.0, 100.0))
t('C6: simultaneous opposite signals -> both stand down',
  r2 is None and co.position is None and
  co.log[-1]['reason'] == 'SIMULTANEOUS_DIRECTION_CONFLICT')

# C7: risk and data suppression
co = mkco()
ra = co.on_signal(10.0, 'A2', +1, 100.0, ['L1'], 'r1',
                  deep_quotes(10.0, 100.0), risk_ok=False)
rb = co.on_signal(11.0, 'A2', +1, 100.0, ['L1'], 'r2',
                  deep_quotes(11.0, 100.0), data_ok=False)
t('C7: RISK_SUPPRESSED and DATA_SUPPRESSED recorded',
  ra is None and rb is None and
  [x['reason'] for x in co.log] == ['RISK_SUPPRESSED',
                                    'DATA_SUPPRESSED'])

# C8: EXECUTION_MISSED on an empty/illiquid stream
co = mkco()
rm = co.on_signal(10.0, 'A2', +1, 100.0, ['L1'], 'm1', [])
t('C8: EXECUTION_MISSED recorded; no position opened',
  rm is None and co.position is None and
  co.log[-1]['reason'] == 'EXECUTION_MISSED')

# C9: frozen re-arm — immediate same-setup repeat suppressed; trades
# again after 60s or a >=4-tick displaced trigger
co = mkco()
r1 = co.on_signal(10.0, 'A2', +1, 100.0, ['L1'], 'k1',
                  deep_quotes(10.0, 100.0))
co.on_exit(r1['id'], 20.0, 101.0)
r2 = co.on_signal(25.0, 'A2', +1, 100.1, ['L1'], 'k2',
                  deep_quotes(25.0, 100.0))
r3 = co.on_signal(25.5, 'A2', +1, 100.0 - 1.0, ['L1'], 'k3',
                  deep_quotes(25.5, 100.0))
t('C9: re-arm blocks an immediate repeat; a displaced trigger re-arms',
  r2 is None and co.log[-2]['reason'] == 'REARM_PENDING' and
  r3 is not None)
co.on_exit(r3['id'], 30.0, 101.0)
r4 = co.on_signal(95.0, 'A2', +1, 100.0 - 1.0, ['L1'], 'k4',
                  deep_quotes(95.0, 100.0))
t('C9b: 60s after flat the same setup re-arms', r4 is not None)

# internal eligibility (repair 9, coordinator side)
co = mkco()
rn = co.on_signal(10.0, 'A2', +1, 150.0, ['L1'], 'n1',
                  deep_quotes(10.0, 150.0))
t('coordinator enforces active-level eligibility internally',
  rn is None and co.log[-1]['reason'] == 'NOT_AT_ACTIVE_LEVEL')

# =====================================================================
# SPECIFICATION REPAIRS
# =====================================================================
# R1: strict 20-session baseline
sb = CO.StrictBaseline(n_sessions=20)
for ses in range(19):
    sb.observe('f', 34500, 10.0 + 0.1 * ses)
    sb.close_session()
z19 = sb.z('f', 34500, 12.0)
sb.observe('f', 34500, 11.9)
sb.close_session()
z20 = sb.z('f', 34500, 12.0)
t('R1: standardized features need ALL 20 prior sessions (19 -> None)',
  z19 is None and z20 is not None)

# R2/R3: strict H1 formation — contract identity + alignment + rolls
def hb(t0, o, h, l, c, contract='NQ 09-26'):
    return dict(t_open=t0, t_close=t0 + 3600, o=o, h=h, l=l, c=c,
                contract=contract, last_event_t=t0 + 3600,
                instrument='NQ')


BARS = ([hb(i * 3600, 100, 101 + i * 0.1, 99, 100.5) for i in range(5)] +
        [hb(5 * 3600, 100.4, 100.9, 100.0, 100.6),
         hb(6 * 3600, 100.5, 100.8, 100.1, 100.4),
         hb(7 * 3600, 100.5, 106.0, 100.3, 105.5)])
TRZ = [None] * 5 + [-0.5, -0.2, 3.0]
t('R2: strict construction still forms the valid fixture zone',
  CO.find_zone_at_strict(BARS, TRZ, 7) is not None)
B2 = [dict(b) for b in BARS]
B2[6]['contract'] = 'NQ 12-26'
t('R3: a contract roll inside the window kills the zone',
  CO.find_zone_at_strict(B2, TRZ, 7) is None)
B3 = [dict(b) for b in BARS]
B3[6]['t_open'] += 7200
B3[6]['t_close'] += 7200
t('R2b: session/calendar misalignment kills the zone',
  CO.find_zone_at_strict(B3, TRZ, 7) is None)

# R4: liquidity-aware fills
qs = [(10.2, 100.00, 5, 100.25, 3), (10.4, 100.00, 5, 100.50, 4)]
f = CO.fill_with_liquidity(qs, 10.0, +1, 5)
t('R4: partial fills sweep displayed liquidity at successive quotes',
  f['filled'] == 5 and f['partial'] is False and len(f['legs']) == 2 and
  abs(f['vwap'] - (3 * 100.25 + 2 * 100.50) / 5) < 1e-9)
f2 = CO.fill_with_liquidity(qs, 10.0, +1, 10)
t('R4b: requested > displayed leaves an honest partial',
  f2['filled'] == 7 and f2['partial'] is True)
f3 = CO.fill_with_liquidity([(30.0, 100, 5, 100.25, 5)], 10.0, +1, 1)
t('R4c: nothing executable inside the frozen window -> MISSED',
  f3['missed'] is True)

# R5: 30-minute cap precedence
qcap = [(21.0, 100.60, 5, 100.85, 5),
        (10.0 + 1801.0, 100.40, 5, 100.65, 5)]
res = CO.simulate_capped(qcap, 100.50, 10.0, +1, 99.50,
                         check_10s=lambda tw: (2, 4),
                         check_control_loss=lambda tw: (1.5, True))
t('R5: a control-loss signal AFTER the 30m deadline cannot fire; '
  'TIME_30M wins', res['exit'] == 'TIME_30M')

# R6: bounded adverse share + renamed polarity
zsize = lambda sz: (sz - 50) / 10.0
trs = [(0, 0, 90, -1), (1, 0, 80, +1), (2, 0, 5, -1)]
bd = CO.adverse_large_print_share_bounded(trs, +1, zsize)
t('R6: bounded share in [0,1] = adverse large volume / total large',
  abs(bd['share'] - 90 / 170) < 1e-9 and 0 <= bd['share'] <= 1)
pol = CO.adverse_large_print_polarity(trs, +1, zsize)
t('R6b: predecessor signed value preserved under the polarity name',
  abs(pol['share'] - (90 - 80) / 170) < 1e-6)

# R7: direct A5 tests
f5 = dict(trend_dir=1, adverse_z=2.2, adverse_progress_ticks=1,
          replenish_z=1.7, trend_flip_z=1.1)
t('R7: A5 fires with the prior trend on absorbed pullback',
  SIG.a5_pullback_resumption(f5) == 1)
t('R7b: A5 silent without trend state',
  SIG.a5_pullback_resumption(dict(f5, trend_dir=0)) == 0)
t('R7c: A5 silent when pullback replenishment is weak',
  SIG.a5_pullback_resumption(dict(f5, replenish_z=1.4)) == 0)
t('R7d: A5 mirror (downtrend -> short)',
  SIG.a5_pullback_resumption(dict(f5, trend_dir=-1)) == -1)

# R8: genuine toggle-off bit-for-bit parity (signals, fills, P&L)
qfix = [(10.2 + i, 100.25 + 0.25 * i, 50, 100.50 + 0.25 * i, 50)
        for i in range(12)]
fix = dict(t=10.0, dir=+1, level=100.25, stop=99.50, quotes=qfix,
           check_10s=lambda tw: (2, 4),
           check_cl=lambda tw: (0.0, False))
h_pred = CO.digest(CO.run_predecessor(fix))
h_pass = CO.digest(CO.run_through_coordinator_passthrough(fix))
t('R8: coordinator passthrough reproduces the predecessor bit-for-bit',
  h_pred == h_pass)

# R9: integrated wall gate — eligibility + dedup inside the engine
gate = CO.IntegratedWallGate({'L1': 100.0}, 1.0)
ep, why = gate.open_episode(100.25, 100, 4.0, +1, ['L1'])
t('R9: wall episode at an active level opens', why == 'NEW' and
  isinstance(ep, WE.WallEpisode))
ep2, why2 = gate.open_episode(100.25, 100, 4.0, +1, ['L1B'])
t('R9b: same physical wall re-labeled -> OVERLAP_SUPPRESSED, one episode',
  why2 == 'OVERLAP_SUPPRESSED' and ep2 is ep and
  set(ep.level_ids) >= {'L1', 'L1B'})
ep3, why3 = gate.open_episode(150.0, 100, 4.0, +1, ['far'])
t('R9c: wall away from every active level refused INSIDE the engine',
  ep3 is None and why3 == 'NOT_AT_ACTIVE_LEVEL')

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
