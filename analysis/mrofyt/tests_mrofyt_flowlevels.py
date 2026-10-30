#!/usr/bin/env python3
# MROF-YT-W7-FLOWLEVELS-1.0 suite. The levels, events, grade and exits
# are exercised on hand-built paths and grids with known answers, the
# search tree against a brute-force scan, and the pipeline end to end on
# synthetic recorder-format runs (mles_v12_synth). Synthetic events
# verify CODE BEHAVIOR only, never market evidence. No order, fill or
# P&L exists anywhere.
import array
import calendar
import hashlib
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_bigmove as BM      # noqa: E402
import mrofyt_context as CX      # noqa: E402
import mrofyt_discover as DI     # noqa: E402
import mrofyt_flowlevels as F    # noqa: E402
import mrofyt_runner as RUN      # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w7_')
TK = 0.25
A = lambda xs: array.array('d', xs)     # noqa: E731
# 2026-09-02 14:00 UTC = 10:00 ET (EDT)
T0 = float(calendar.timegm((2026, 9, 2, 14, 0, 0)))
assert RUN.sod_seconds(T0) == 10 * 3600


def mkpath(pts):
    ts, ps = A([a for a, _ in pts]), A([b for _, b in pts])
    return ts, ps, F.Tree(list(ps))


def mkgrid(rows, t0=T0):
    """rows: [(dt, D, z, resp, mid, D60)] -> grid records, times."""
    g = [dict(t=t0 + dt, D=D, z_delta_s=z, resp=r, mid=m, D60=d60,
              w7_lv=(None,) * 7) for dt, D, z, r, m, d60 in rows]
    return g, [x['t'] for x in g]


# ---------------------------------------------------------------------
# FL1: the search tree against a brute-force scan
# ---------------------------------------------------------------------
rng = random.Random(7)
bad = checks = 0
for trial in range(40):
    n = rng.choice([1, 2, 3, 7, 64, 100, 513])
    ps = [15000 + rng.choice([-1, 1]) * TK * rng.randint(0, 40)
          for _ in range(n)]
    tr = F.Tree(ps)
    for _ in range(40):
        lo = rng.randint(0, n - 1)
        hi = rng.randint(lo, n - 1)
        x = rng.choice(ps) + rng.choice([-TK, 0, TK])
        seg = ps[lo:hi + 1]
        ge = next((j for j in range(lo, hi + 1) if ps[j] >= x), None)
        le = next((j for j in range(lo, hi + 1) if ps[j] <= x), None)
        checks += 1
        if (tr.range_max(lo, hi) != max(seg) or
                tr.range_min(lo, hi) != min(seg) or
                tr.first_ge(lo, hi, x) != ge or tr.first_le(lo, hi, x) != le
                or tr.first_beyond(lo, hi, -1, x) != le or
                tr.best(lo, hi, 1) != max(seg)):
            bad += 1
t('FL1: range max/min and first-crossing search agree with a brute-force '
  'scan on %d random checks; an empty range gives nothing' % checks,
  checks == 1600 and bad == 0 and F.Tree([1.0]).first_ge(3, 2, 0) is None
  and F.Tree([1.0, 2.0]).range_max(5, 9) == -math.inf)

# ---------------------------------------------------------------------
# FL2: swing levels
# ---------------------------------------------------------------------
M0 = int(T0 // 60)
prices = [1, 2, 3, 4, 5, 10, 5, 4, 10, 2, 1, 0.5, 3]
sts = [(M0 + m) * 60 + 1.0 for m in range(len(prices))]
sw = F.swing_levels(A(sts), A(prices))
sw_gap = F.swing_levels(A(sts[:7] + sts[9:]), A(prices[:7] + prices[9:]))
t('FL2: a one-minute bar high strictly above the 5 before and not below '
  'the 5 after is a SWING_H known at the end of the 5th bar after it; an '
  'equal later high still counts; fewer than 4 recorded bars on a side '
  'gives none',
  (float((M0 + 11) * 60), 10.0, 'SWING_H') in sw and
  all(x[2] != 'SWING_L' or x[1] != 10.0 for x in sw) and
  not any(x[1] == 10.0 for x in sw_gap))

# ---------------------------------------------------------------------
# FL3: absorption, value area, merging
# ---------------------------------------------------------------------
gA, _ = mkgrid([(10, 50, 3.5, 0.5, 100.0, 0), (20, 50, 3.5, 2.0, 101.0, 0),
                (30, 50, 2.9, 0.0, 102.0, 0), (40, -50, 3.0, -1.0, 99.0, 0)])
ab = F.absorption_levels(gA)
prev = [dict(mid=100.25, vol10=500.0), dict(mid=101.5, vol10=200.0),
        dict(mid=99.0, vol10=100.0), dict(mid=None, vol10=50.0)]
vl = F.value_levels(prev, 5.0)
poc, vah, val = CX.value_area({100: 500.0, 101: 200.0, 99: 100.0})
mg = F.merge_levels([(1, 100.0, 'A'), (2, 100.5, 'B'), (3, 100.75, 'C'),
                     (0, 99.0, 'D')])
t('FL3: absorption = z >= 3 with at most a tick of progress (either side);'
  ' the value area is the context study\'s on the previous session\'s 10 s '
  'volume; a level within 2 ticks of an earlier one is dropped',
  [x[1] for x in ab] == [100.0, 99.0] and
  vl == [(5.0, poc, 'POC'), (5.0, vah, 'VAH'), (5.0, val, 'VAL')] and
  poc == 100.5 and F.value_levels([], 5.0) == [] and
  mg == [(0, 99.0, 'D'), (1, 100.0, 'A'), (3, 100.75, 'C')])

# ---------------------------------------------------------------------
# FL4: events
# ---------------------------------------------------------------------
PF = mkpath([(T0, 99.0), (T0 + 30, 99.5), (T0 + 60, 100.5),
             (T0 + 70, 101.0), (T0 + 90, 99.75), (T0 + 200, 97.0),
             (T0 + 400, 90.0)])
rows = [(dt, 0, 0.0, 0.0, 99.0, 0) for dt in range(10, 60, 10)]
rows += [(60, 40, 2.0, 2.0, 100.5, 0), (70, 30, 1.0, 1.0, 101.0, 0),
         (80, 10, 0.5, 0.0, 100.5, 0), (90, -50, 2.5, -3.0, 99.75, 0)]
rows += [(dt, -10, 0.5, -1.0, 97.0, -60) for dt in range(100, 600, 10)]
gF, gtF = mkgrid(rows)
LV = (T0, 100.0, 'SWING_H')
evF = F.detect(LV, PF, gF, gtF)
rows_noflip = [r if r[0] != 90 else (90, 50, 2.5, -3.0, 99.75, 0)
               for r in rows]
rows_noflip = [r if not 90 < r[0] <= 110 else (r[0], 5, 0.2, 0, 97.0, 0)
               for r in rows_noflip]
gN, gtN = mkgrid(rows_noflip)
early = 3600 * 6.0      # 04:00 ET
PFe = mkpath([(a - early, b) for a, b in zip(PF[0], PF[1])])
gE, gtE = mkgrid(rows, T0 - early)
t('FL4: FAILED: a 2-tick break, back a tick through within 120 s, the flow '
  'turning (z >= 1) within 20 s: fade at that tick; the stop is 2 ticks '
  'past the sweep extreme, clamped to 12; trapped = the break side\'s '
  'aggression from break to entry; no turn or outside 09:30-15:30: none',
  evF and evF['kind'] == 'FAILED' and evF['direction'] == -1 and
  evF['t_entry'] == T0 + 90 and evF['p0'] == 99.75 and
  evF['extreme'] == 101.0 and evF['stop_ticks'] == 12.0 and
  evF['trapped'] == 80.0 and evF['flip_z'] == 2.5 and evF['fresh'] and
  F.detect(LV, PF, gN, gtN) is None and
  F.detect((T0 - early, 100.0, 'SWING_H'), PFe, gE, gtE) is None)

PH = mkpath([(T0, 99.0), (T0 + 60, 100.5), (T0 + 100, 101.0),
             (T0 + 200, 102.0), (T0 + 300, 112.0), (T0 + 900, 125.0)])
rowsH = [(dt, 20, 1.0, 1.0, 100.75, 30) for dt in range(10, 900, 10)]
rowsH = [r if r[0] != 180 else (180, 60, 2.4, 2.0, 101.0, 60) for r in rowsH]
gH, gtH = mkgrid(rowsH)
evH = F.detect(LV, PH, gH, gtH)
rowsHn = [(r[0], -20 if 60 <= r[0] <= 180 else r[1]) + r[2:] for r in rowsH]
gHn, gtHn = mkgrid(rowsHn)
PHshort = mkpath([(T0, 99.0), (T0 + 60, 100.5), (T0 + 100, 101.0)])
t('FL4b: HELD: beyond for 120 s with net flow in the break direction: '
  'follow at the first grid tick at or after 120 s; the stop is 2 ticks '
  'back through the level (clamped); against the flow, or a run that ends '
  'first: none',
  evH and evH['kind'] == 'HELD' and evH['direction'] == 1 and
  evH['t_entry'] == T0 + 180 and evH['p0'] == 101.0 and
  evH['stop_ticks'] == 12.0 and evH['flip_z'] == 2.4 and
  evH['trapped'] == 0.0 and
  F.detect(LV, PH, gHn, gtHn) is None and
  F.detect(LV, PHshort, gH, gtH) is None)

PA = mkpath([(T0, 100.0), (T0 + 10, 100.25), (T0 + 20, 99.5),
             (T0 + 30, 101.0)])
PA2 = mkpath([(T0, 100.0), (T0 + 10, 100.5), (T0 + 20, 99.0)])
t('FL4c: which way a level breaks: a swing high up, a swing low down, '
  'any other level away from the side price first leaves it to (2 ticks)',
  F._side((T0, 100.0, 'ABSORPTION'), PA[0], PA[1], PA[2]) == (2, 1) and
  F._side((T0, 100.0, 'POC'), PA2[0], PA2[1], PA2[2]) == (1, -1) and
  F._side((T0, 100.0, 'SWING_L'), PA[0], PA[1], PA[2]) == (0, -1) and
  F._side((T0, 102.0, 'VAH'), PA[0], PA[1], PA[2]) == (0, 1) and
  F._side((T0 - 5, 100.0, 'VAL'), PA[0], PA[1], PA[2]) == (None, 0))

# FRESH and ABSORPTION on the FAILED path
PFn = mkpath([(T0, 99.0), (T0 + 30, 99.75), (T0 + 40, 99.0),
              (T0 + 200, 100.5), (T0 + 210, 101.0), (T0 + 230, 99.75),
              (T0 + 400, 95.0)])
rowsA = [(dt, 0, 0.0, 0.0, 99.0, 0) for dt in range(10, 200, 10)]
rowsA[2] = (30, 60, 2.5, 0.5, 99.75, 0)       # longs absorbed at the level
rowsA += [(200, 40, 2, 1, 100.5, 0), (210, 30, 1, 1, 101.0, 0),
          (220, 5, 0.1, 0, 100.0, 0), (230, -50, 1.2, -3, 99.75, 0)]
rowsA += [(dt, -10, 0.5, -1.0, 96.0, -60) for dt in range(240, 600, 10)]
gFA, gtFA = mkgrid(rowsA)
evFA = F.detect(LV, PFn, gFA, gtFA)
t('FL4d: FRESH fails when the mid came within 2 ticks of the level before '
  'the approach; ABSORPTION holds when the trapped side hit z >= 2 near '
  'the level and price moved a tick or less',
  evF['absorbed'] is False and evFA and evFA['fresh'] is False and
  evFA['absorbed'] is True and evFA['t_entry'] == T0 + 230)

# ---------------------------------------------------------------------
# FL5: the grade
# ---------------------------------------------------------------------
base = dict(trapped=80.0, absorbed=True, flip_z=2.5, fresh=True,
            confluence=True, level=100.0, type='POC', daily=[])
t('FL5: one point each for trapped (>= cut), absorption, a strong turn, '
  'fresh, confluence; 4-5 A+, 3 A, 2 B, 0-1 skip; no frozen cut: no '
  'trapped point',
  F.points(base, 80.0) == 5 and F.points(base, 81.0) == 4 and
  F.points(dict(base, flip_z=1.9, fresh=False), 81.0) == 2 and
  F.points(dict(base, flip_z=None), None) == 3 and
  [F.grade_of(p) for p in range(6)] == ['SKIP', 'SKIP', 'B', 'A', 'A+',
                                         'A+'])
pv = [(0, 100.0, 'POC'), (0, 110.0, 'VAH'), (0, 90.0, 'VAL')]
t('FL5b: confluence = within 8 ticks of a daily level or of yesterday\'s '
  'value area, the level itself excluded',
  F.confluence(dict(base, daily=[]), pv) is False and
  F.confluence(dict(base, daily=[102.0]), pv) is True and
  F.confluence(dict(base, daily=[102.25]), pv) is False and
  F.confluence(dict(base, type='SWING_H'), pv) is True and
  F.confluence(dict(base, type='SWING_H', level=108.0), pv) is True)

# ---------------------------------------------------------------------
# FL6: the exits
# ---------------------------------------------------------------------
ev = dict(direction=1, p0=100.0, stop_ticks=12.0, i0=0, t_entry=T0,
          sod=10 * 3600)
t('FL6: E1\'s target is the nearest level ahead if it is >= 1.5 x stop '
  'away (no cap); a nearer level means no E1 trade; no level: max(0.2 x '
  'the daily range, 1.5 x stop); levels behind are ignored',
  F.next_target(ev, [105.0, 120.0, 90.0], 50.0) == 20.0 and
  F.next_target(ev, [102.5, 120.0], 50.0) is None and
  F.next_target(ev, [90.0], 50.0) == 40.0 and
  F.next_target(ev, [], None) == 18.0 and
  F.next_target(dict(ev, direction=-1), [95.0, 104.0], None) == 20.0)

PB = mkpath([(T0, 100.0), (T0 + 10, 101.0), (T0 + 20, 97.0),
             (T0 + 30, 106.0)])
PB2 = mkpath([(T0, 100.0), (T0 + 10, 104.0), (T0 + 20, 96.0)])
PB3 = mkpath([(T0, 100.0), (T0 + 10, 101.0), (T0 + 7200, 102.0),
              (T0 + 30000, 130.0)])
t('FL6b: the bracket: the first mid at or beyond the stop or the target '
  'decides; neither by 15:59 ET (or 3 h): out at the mid (TIME)',
  F.bracket(PB, ev, 12, 20) == ('STOP', -12, T0 + 20) and
  F.bracket(PB2, ev, 12, 16) == ('TARGET', 16, T0 + 10) and
  F.bracket(PB3, ev, 12, 200) == ('TIME', 8.0, T0 + 7200) and
  F.bracket(PB3, dict(ev, sod=15 * 3600 + 58 * 60), 12, 200) ==
  ('TIME', 4.0, T0 + 10))

PT = mkpath([(T0, 100.0), (T0 + 10, 100.5), (T0 + 20, 101.0),
             (T0 + 30, 101.5), (T0 + 400, 101.5)])
gT, gtT = mkgrid([(10, 0, 0, 0, 100.5, -1),       # FADE alone
                  (20, -40, 3, -1, 101.0, 5),     # AGAINST alone
                  (30, 40, 3, 0.5, 101.5, 5),     # ABSORBED alone
                  (40, 40, 3, 1.0, 101.5, -5),    # FADE + ABSORBED
                  (50, 0, 0, 0, 101.5, -5)])
gS, gtS = mkgrid([(dt, 5, 0.1, 0.0, 101.5, 5 if dt < 150 else -5)
                  for dt in range(10, 300, 10)])
t('FL6c: the tape exit needs 2 of FADE / AGAINST / ABSORBED / STALL at '
  'one grid tick: one sign alone never exits; FADE with ABSORBED does; a '
  '120 s stall since the best mid with a faded 60 s flow does',
  F.tape_exit(PT, ev, gT, gtT, 30.0, T0 + 1000) == (T0 + 40, 101.5) and
  F.tape_exit(PT, ev, gT[:3], gtT[:3], 30.0, T0 + 1000) is None and
  F.tape_exit(PT, ev, gS, gtS, 30.0, T0 + 1000) == (T0 + 150, 101.5) and
  F.tape_exit(PT, ev, gS, gtS, 30.0, T0 + 140) is None)

evx = dict(ev, target_e1=4.0)
xs = F.exits(evx, PT, gT, gtT, 30.0)
evy = dict(ev, target_e1=None)
xs2 = F.exits(evy, PB, gT[:3], gtT[:3], 30.0)
t('FL6d: E2 = tape exit with the stop behind it; E3 = half E1, half E2, '
  'busy until both are out; E4 = 100/60; no E1 target: no E1 or E3',
  xs['E1'] == ('TARGET', 4.0, 12.0, T0 + 20) and
  xs['E2'] == ('TAPE', 6.0, 12.0, T0 + 40) and
  xs['E3'] == ('TARGET/TAPE', 5.0, 12.0, T0 + 40) and
  xs['E4'][0] == 'TIME' and xs['E4'][2] == 60.0 and
  set(xs2) == {'E2', 'E4'} and xs2['E2'] == ('STOP', -12.0, 12.0, T0 + 20))

# ---------------------------------------------------------------------
# FL7: statistics
# ---------------------------------------------------------------------
e_nq = dict(instrument='NQ', session='1')
e_mnq = dict(instrument='MNQ', session='1')
t('FL7: net of costs: NQ 2 ticks (3 on a stop), MNQ 5 (6); the hybrid\'s '
  'halves charged half each; R = net / stop',
  F.net_r(e_nq, ('TARGET', 20.0, 12.0, 0)) == (1.5, 4.5) and
  F.net_r(e_nq, ('STOP', -12.0, 12.0, 0)) == (-15 / 12.0, -3.75) and
  F.net_r(e_nq, ('TARGET/STOP', 4.0, 12.0, 0))[1] == 0.375 and
  F.net_r(e_mnq, ('TAPE', 5.0, 10.0, 0)) == (0.0, 0.0))
rows1 = [(dict(t_entry=0), ('X', 1, 1, 50)), (dict(t_entry=40), ('X', 1, 1, 60)),
         (dict(t_entry=50), ('X', 1, 1, 70)), (dict(t_entry=70), ('X', 1, 1, 80))]
taken = F.one_at_a_time(list(reversed(rows1)))
rp = random.Random(3)
planted, flat = [], []
for s in range(30):
    for _ in range(8):
        p = rp.randint(0, 5)
        v = 4.0 * (p - 2.5) + rp.gauss(0, 3)
        planted.append((dict(instrument='NQ', session='s%d' % s, points=p),
                        ('TIME', v + 2.0, 12.0, 0)))
        flat.append((dict(instrument='NQ', session='s%d' % s, points=p),
                     ('TIME', rp.gauss(0, 12), 12.0, 0)))
sl, sf = F.test_slope(planted), F.test_slope(flat)
t('FL7b: one position at a time skips an entry before the taken trade is '
  'out (an entry AT the exit is taken); the clustered grade slope finds a '
  'planted rise and not a flat one',
  [r[0]['t_entry'] for r in taken] == [0, 50, 70] and
  sl['slope_r_per_point'] > 0.25 and sl['p'] < 0.001 and
  sl['ci95'][0] > 0 and sf['p'] > 0.01)

# ---------------------------------------------------------------------
# FL8-FL9: end to end on synthetic tape
# ---------------------------------------------------------------------
def _path(amp):
    return lambda i: 15000.0 + amp * math.sin(2 * math.pi * (i * 0.05) /
                                              900.0)


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w7c%d' % i, session=ses,
                 seed=i)
rep5, frz5, r5 = F.run_dev(D5)
ev5, _c5 = F.build(r5, frz5)
nq = {x['test']: x for x in rep5['results'].get('NQ', {}).get('tests', [])}
tc = sorted(e['trapped'] for e in ev5 if e['instrument'] == 'NQ' and
            e['kind'] == 'HELD')
t('FL8: end to end: events carry level, kind, grade and every exit; stops '
  'lie in 12..60; the nine tests are scored; the trapped cut is the DEV '
  'median; the validation session is refused; report renders',
  ev5 and all(12 <= e['stop_ticks'] <= 60 and 'E4' in e['exits'] and
              'E2' in e['exits'] and e['grade'] == F.grade_of(e['points'])
              for e in ev5) and
  set(nq) == {'F1', 'F2', 'F3', 'F4', 'H1', 'H2', 'H3', 'H4', 'G'} and
  (not tc or frz5['trapped']['NQ|HELD'] == tc[len(tc) // 2]) and
  frz5['big_d'].get('NQ') is not None and
  rep5['sessions_refused'] == ['20260921'] and
  json.dumps(rep5, default=str) and 'H4' in F.text(rep5) and
  all(r5.grid[0].get(k) is not None for k in ('vol10', 'w7_lv')))
repE, _rE = F.run_evaluate(D5, frz5)
repU, _rU = F.run_evaluate(D5, frz5, unblind=True)
eG = {x['test']: x for x in repE['results']['NQ']['tests']}
t('FL8b: --evaluate on DEV with the frozen cuts reproduces the DEV numbers '
  'and says so; with --unblind it evaluates only sessions after 20260918',
  all(eG[k].get('n') == nq[k].get('n') and
      eG[k].get('mean_net_r') == nq[k].get('mean_net_r') for k in nq) and
  all('reproduction' in x['status'] for x in eG.values()) and
  all(s > F.DEV_END for s in repU['sessions_evaluated']) and
  '20260921' in repU['sessions_inspected'])

D6 = os.path.join(WORK, 'replay')
for i, ses in enumerate(('20260730', '20260731', '20260803', '20260804')):
    SY.synth_run(D6, n_depth=40000, dt_step=0.05, price_path=_path(30 + i),
                 trade_every=10, quote_every=5, cid='rp%d' % i, session=ses,
                 seed=i)
repH, _rH = F.run_evaluate(D6, frz5, holdout=True)
D7 = os.path.join(WORK, 'replay_bad')
shutil.copytree(D6, D7)
SY.synth_run(D7, n_depth=20000, dt_step=0.05, price_path=_path(30),
             trade_every=10, quote_every=5, cid='late', session='20260902',
             seed=9)
fz = os.path.join(WORK, 'frozen.json')
json.dump(frz5, open(fz, 'w'))
buf = io.StringIO()
with redirect_stdout(buf):
    rc_null = F.main([D7, '--evaluate', os.devnull, '--holdout'])
    rc_bad = F.main([D7, '--evaluate', fz, '--holdout'])
    rc_u = F.main([D5, '--unblind'])
    rc_h = F.main([D5, '--holdout'])
    rc_uh = F.main([D5, '--evaluate', fz, '--unblind', '--holdout'])
t('FL9: a replay holdout folder is read whole when every session is before '
  '2026-09-01, and STOPPED when it holds a recorded session; a file that is '
  'not the frozen cut is refused; --unblind / --holdout without '
  '--evaluate, or together, are refused',
  repH['holdout'] and repH['sessions_inspected'][0] == '20260730' and
  repH['sessions_refused'] == [] and rc_bad == 2 and rc_null == 2 and
  'not a wave-seven frozen file' in buf.getvalue() and
  'only sessions before 20260901' in buf.getvalue() and
  rc_u == 2 and rc_h == 2 and rc_uh == 2)

# ---------------------------------------------------------------------
# FL10-FL11: nothing frozen changed; an abandoned run leaves nothing
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
rA = DI.DiscoverRunner(D5)
ledA = rA.run()
rB = F.FlowRunner(D5)
ledB = rB.run()
strip = lambda gs: [dict((k, v) for k, v in g.items()   # noqa: E731
                         if k not in ('vol10', 'w7_lv')) for g in gs]
t('FL10: the wave-seven runner leaves wave four\'s grid, wave three\'s '
  'fires and the wave-one ledger identical, and the signal module keeps '
  'its pinned hash',
  strip(rB.grid) == rA.grid and rB.w3_fires == rA.w3_fires and
  json.dumps({k: ledA.get(k) for k in _CMP}, sort_keys=True,
             default=str) ==
  json.dumps({k: ledB.get(k) for k in _CMP}, sort_keys=True,
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
r9a = F.FlowRunner(d9a)
r9a.run()
r9b = F.FlowRunner(d9b)
r9b.run()
e9a, _ = F.build(r9a)
e9b, _ = F.build(r9b)
_reg = open(os.path.join(HERE, F.REGISTRATION)).read()
t('FL11: an abandoned run is wound back whole (grid with its volume and '
  'levels, mid series), so it adds no event; the registration states the '
  'levels, the grade, the four exits, the holdout rule and Holm',
  r9a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  r9a.grid == r9b.grid and
  json.dumps([dict((k, e[k]) for k in F._SLIM) for e in e9a],
             default=str) ==
  json.dumps([dict((k, e[k]) for k in F._SLIM) for e in e9b],
             default=str) and
  all(w in _reg for w in ('SWING_H', 'ABSORPTION', 'POC', 'TRAPPED',
                          'FRESH', 'CONFLUENCE', 'E1 NEXT LEVEL',
                          'E2 TAPE', 'E3 HYBRID', 'E4 BASELINE',
                          '2026-09-01', 'Holm over the nine',
                          'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
