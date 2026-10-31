#!/usr/bin/env python3
# MROF-YT-W10-CLOSERECLAIM-1.0 suite. Candles, the break-and-reclaim
# episode and the order-flow filter are exercised on hand-built closes
# and grids with known answers, and the pipeline end to end on synthetic
# recorder-format runs (mles_v12_synth). Synthetic events verify CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import array
import collections
import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_closereclaim as C  # noqa: E402
import mrofyt_l2targets as W     # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w10_')
A = lambda xs: array.array('d', xs)     # noqa: E731

# ---------------------------------------------------------------------
# CR1: sides and candles
# ---------------------------------------------------------------------
t('CR1: a close is above / below a level at 1 tick or more, otherwise at '
  'it; every clock minute gets the last mid before it ends, carried '
  'through a minute without a change',
  C.side(100.25, 100.0) == 1 and C.side(99.75, 100.0) == -1 and
  C.side(100.0, 100.0) == 0 and C.side(100.1, 100.0) == 0 and
  C.side(None, 100.0) == 0 and C.side(100.5, None) == 0 and
  C.minute_closes(A([60.5, 61, 125, 250]), A([1, 2, 3, 4])) ==
  [(1, 2.0), (2, 3.0), (3, 3.0), (4, 4.0)] and
  C.minute_closes(A([]), A([])) == [])


# ---------------------------------------------------------------------
# CR2-CR3: the episode and the filter
# ---------------------------------------------------------------------
def grid(minutes, flows=None, drop=()):
    """{t: record} with YDAY_HIGH = 100.0; flows: {minute: (D, z)} for
    every tick of that minute (default no aggression)."""
    flows = flows or {}
    gm = {}
    for m in minutes:
        D, z = flows.get(m, (0.0, None))
        for j in range(1, 7):
            tt = m * 60 + 10 * j
            if tt in drop:
                continue
            gm[tt] = dict(t=float(tt), instrument='NQ', session='20260902',
                          run='r1', D=D, z_delta_s=z,
                          w10_lv=(100.0, None, None, None, None, None))
    return gm


closes = [(10, 99.0), (11, 100.5), (12, 101.0), (13, 99.5), (14, 99.0),
          (15, 100.25)] + [(m, 101.0) for m in range(16, 22)] + \
    [(22, 99.5), (23, 100.5)]
gm = grid(range(10, 24), flows={13: (-20.0, 1.5), 23: (-5.0, 2.0)})
cnt = collections.Counter()
ev = C.episodes(closes, gm, cnt)
t('CR2: a close through the level, then a close back within 5 candles is '
  'one event at the reclaim close, faded; a break still beyond after 5 '
  'candles held (no trade) and the close back after it is a new break the '
  'other way; breaks are numbered per level and session',
  [(e['test_no'], e['b'], e['direction'], e['m_break'], e['m_reclaim'],
    e['t']) for e in ev] ==
  [(1, 1, -1, 11, 13, 840.0), (3, -1, 1, 22, 23, 1440.0)] and
  cnt[('NQ', '20260902', 'YDAY_HIGH')] == 3 and
  ev[0]['level'] == 100.0 and ev[0]['level_id'] == 'YDAY_HIGH')
t('CR3: the order-flow filter needs the reclaim candle\'s net aggression '
  'against the break AND the 10 s ending at the close against it with z >= '
  '1.0; aggression with the break fails it',
  ev[0]['flow'] is True and ev[1]['flow'] is False and
  C.flow_ok(grid([13], {13: (-20.0, 0.9)}), 13, 1) is False and
  C.flow_ok(grid([13], {13: (20.0, 1.5)}), 13, 1) is False and
  C.flow_ok(grid([13], {13: (-20.0, 1.0)}), 13, 1) is True and
  C.flow_ok({}, 13, 1) is False)

closes2 = [(10, 99.0), (11, 100.5)] + [(m, 101.0) for m in range(12, 17)] + \
    [(17, 99.5)]
drop2 = {m * 60 + 60 for m in range(12, 17)}
ev2 = C.episodes(closes2, grid(range(10, 18), drop=drop2),
                 collections.Counter())
closes3 = [(10, 99.0), (11, 100.5), (16, 99.5)]
ev3 = C.episodes(closes3, grid(range(10, 17)), collections.Counter())
t('CR3b: the five candles are clock minutes: minutes without a grid '
  'record are skipped but still count, so a close back 6 minutes later is '
  'no reclaim; one exactly 5 minutes later is',
  ev2 == [] and len(ev3) == 1 and ev3[0]['m_reclaim'] == 16)


# ---------------------------------------------------------------------
# CR4-CR5: end to end on synthetic tape
# ---------------------------------------------------------------------
def _path(amp):
    return lambda i: 15000.0 + amp * math.sin(2 * math.pi * (i * 0.05) /
                                              900.0)


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w10c%d' % i, session=ses,
                 seed=i)
rep5, r5 = C.run(D5)
ev5 = C.close_events(r5)
sc5 = C.score_close(r5, ev5)
repU, _rU = C.run(D5, unblind=True)
nq = {x['test']: x for x in rep5['tests'].get('NQ', [])}
t('CR4: end to end: candle-close reclaims are found at the six levels, '
  'faded at a minute close within 5 minutes of the break; C1 = the '
  'filtered ones, C2 their first tests, the no-filter and L2 rows beside; '
  'the validation session is refused; the report renders',
  ev5 and all(e['t'] % 60 == 0 and 1 <= e['m_reclaim'] - e['m_break'] <= 5
              and e['direction'] == -e['b'] and e['test_no'] >= 1 and
              e['level_id'] in C.LEVEL_IDS for e in ev5) and
  set(nq) == {'C1', 'C2', 'C0', 'C0F', 'L2', 'L2F'} and
  nq['C0']['n'] == len([x for x in sc5 if x[0]['instrument'] == 'NQ']) and
  nq['C1']['n'] == len([x for x in sc5 if x[0]['instrument'] == 'NQ' and
                        x[0]['flow']]) and
  nq['C2']['n'] <= nq['C1']['n'] and nq['C0F']['n'] <= nq['C0']['n'] and
  nq['L2']['status'] == 'REFERENCE' and
  rep5['sessions_refused'] == ['20260921'] and
  json.dumps(rep5, default=str) and 'C2' in C.text(rep5) and
  all(s > C.DEV_END for s in repU['sessions_evaluated']))

D6 = os.path.join(WORK, 'replay')
for i, ses in enumerate(('20260730', '20260731', '20260803')):
    SY.synth_run(D6, n_depth=30000, dt_step=0.05, price_path=_path(30 + i),
                 trade_every=10, quote_every=5, cid='rp%d' % i, session=ses,
                 seed=i)
repH, _rH = C.run(D6, holdout=True)
D7 = os.path.join(WORK, 'replay_bad')
shutil.copytree(D6, D7)
SY.synth_run(D7, n_depth=20000, dt_step=0.05, price_path=_path(30),
             trade_every=10, quote_every=5, cid='late', session='20260902',
             seed=9)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_bad = C.main([D7, '--holdout'])
    rc_uh = C.main([D5, '--unblind', '--holdout'])
t('CR5: a replay holdout folder is read whole when every session is before '
  '2026-09-01 and STOPPED when it holds a recorded session; --unblind with '
  '--holdout is refused',
  repH['holdout'] and repH['sessions_inspected'][0] == '20260730' and
  rc_bad == 2 and rc_uh == 2 and
  'only sessions before 20260901' in buf.getvalue())

# ---------------------------------------------------------------------
# CR6-CR7: nothing frozen changed; an abandoned run leaves nothing
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
rA = W.TargetRunner(D5)
ledA = rA.run()
rC = C.CloseRunner(D5)
ledC = rC.run()
strip = lambda gs: [dict((k, v) for k, v in g.items()   # noqa: E731
                         if k != 'w10_lv') for g in gs]
t('CR6: the wave-ten runner leaves wave nine\'s grid, fires and ranges and '
  'the wave-one ledger identical, and the signal module keeps its pinned '
  'hash',
  strip(rC.grid) == rA.grid and rC.w3_fires == rA.w3_fires and
  dict(rC.ranges) == dict(rA.ranges) and
  json.dumps({k: ledA.get(k) for k in _CMP}, sort_keys=True,
             default=str) ==
  json.dumps({k: ledC.get(k) for k in _CMP}, sort_keys=True,
             default=str) and
  hashlib.sha256(open(os.path.join(HERE, 'mrofyt_signals.py'),
                      'rb').read()).hexdigest() ==
  '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1')


def _late_corrupt_folder(d, good, bad, **kw):
    for i, ses in enumerate(good):
        SY.synth_run(d, session=ses, cid='g%d' % i, seed=i,
                     price_path=_path(30 + 3 * i), **kw)
    if bad is None:
        return
    mp = SY.synth_run(d, session=bad, cid='bad', seed=99,
                      price_path=_path(45), **kw)
    man = json.load(open(mp))
    dp = os.path.join(d, man['depth']['file'])
    rows = open(dp).read().splitlines(True)
    k = int(len(rows) * 0.9)
    rows[k] = ',' * 3 + ' ' * (len(rows[k]) - 4) + '\n'
    open(dp, 'w').writelines(rows)
    assert os.path.getsize(dp) == man['depth']['bytes']


_G9 = ('20260901', '20260902', '20260903')
d9a, d9b = os.path.join(WORK, 'bad'), os.path.join(WORK, 'ref')
kw9 = dict(n_depth=40000, dt_step=0.05, trade_every=10, quote_every=5)
_late_corrupt_folder(d9a, _G9, '20260904', **kw9)
_late_corrupt_folder(d9b, _G9, None, **kw9)
r9a = C.CloseRunner(d9a)
r9a.run()
r9b = C.CloseRunner(d9b)
r9b.run()
_reg = open(os.path.join(HERE, C.REGISTRATION)).read()
t('CR7: an abandoned run is wound back whole (grid records with their '
  'levels), so it adds no event; the registration states the candle, the '
  '5-candle window, the filter, the two tests, the holdout rule and Holm',
  r9a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  r9a.grid == r9b.grid and
  json.dumps(C.close_events(r9a), sort_keys=True) ==
  json.dumps(C.close_events(r9b), sort_keys=True) and
  all(w in _reg for w in ('one-minute candles', '5 one-minute candles',
                          'z_delta_s >= 1.0', 'C1', 'C2', '2026-09-01',
                          'Holm over the two', 'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
