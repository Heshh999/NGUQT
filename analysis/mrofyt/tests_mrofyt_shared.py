#!/usr/bin/env python3
# Regression suite for the eight code-review fixes to waves seven to
# thirteen (manifest Amendment 36): the shared ledgers, yesterday's value
# levels in a later recording run, HELD still beyond at its entry, a
# WICK window that runs out on the far side, one value-area lookup per
# session, the public Eastern offset, the shared compressed paths and
# wave eight's wind-back log. Hand-built inputs with known answers only;
# synthetic events verify CODE BEHAVIOR, never market evidence. No
# order, fill or P&L exists.
import array
import calendar
import collections
import inspect
import json
import os
import shutil
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mrofyt_bigmove as BM          # noqa: E402
import mrofyt_closereclaim as C      # noqa: E402
import mrofyt_earlylevels as E       # noqa: E402
import mrofyt_flowlevels as F        # noqa: E402
import mrofyt_l2context as X         # noqa: E402
import mrofyt_l2targets as W         # noqa: E402
import mrofyt_l2variants as V        # noqa: E402
import mrofyt_ledgers as LG          # noqa: E402
import mrofyt_levelbreak as LB       # noqa: E402
import mrofyt_pilot as PI            # noqa: E402
import mrofyt_runner as RUN          # noqa: E402
import mrofyt_valuearea as VA        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_shared_')
A = lambda xs: array.array('d', xs)     # noqa: E731
SRC = {m.__name__: open(m.__file__).read() for m in (F, V, W, C, E, X, VA)}
WAVES = ((F, F.W7_VERSION), (V, V.W8_VERSION), (W, W.W9_VERSION),
         (C, C.W10_VERSION), (E, E.W11_VERSION), (X, X.W12_VERSION),
         (VA, VA.W13_VERSION))

# ---------------------------------------------------------------------
# SH1: one copy of the two ledgers (finding 6)
# ---------------------------------------------------------------------
exp_path = os.path.join(WORK, 'exposed.json')
hold_path = os.path.join(WORK, 'holdout.json')
rep = dict(sessions_inspected=['20260921', '20260922'])
for m, _ in WAVES:
    m.record_exposure(rep, exp_path)
    m.record_holdout_read(rep, hold_path)
ex = json.load(open(exp_path))
ho = json.load(open(hold_path))
ref_path = os.path.join(WORK, 'ref.json')
LG.record_exposure(rep, ref_path, F.W7_VERSION)
t('SH1: the seven waves write both ledgers through one shared helper: each '
  'read is listed with its wave\'s version, every inspected day is '
  'EXPOSED_PILOT_DEV once, and no wave keeps its own copy of the rules',
  [r['version'] for r in ho['reads']] == [v for _, v in WAVES] and
  [d['session'] for d in ex['exposed_days']] == ['20260921', '20260922'] and
  all(d['label'] == PI.EXPOSURE_LABEL and
      d['exposed_by'] == F.W7_VERSION and
      d['also_exposed_by'] == [v for _, v in WAVES]
      for d in ex['exposed_days']) and
  json.load(open(ref_path))['rule'] == ex['rule'] and
  all(len(inspect.getsource(f).strip().splitlines()) == 2 and
      'LG.%s(rep, path, ' % f.__name__ in inspect.getsource(f)
      for m, _ in WAVES
      for f in (m.record_exposure, m.record_holdout_read)))

# ---------------------------------------------------------------------
# SH2: yesterday's value levels in a later run (finding 1)
# ---------------------------------------------------------------------
T0 = float(calendar.timegm((2026, 9, 2, 14, 0, 0)))      # 10:00 ET
prior = [(T0 - 14 * 3600, 100.0, 'POC'), (T0 - 14 * 3600, 102.0, 'VAH'),
         (T0 + 10 ** 6, 98.0, 'VAL')]
ts2 = A([T0, T0 + 60, T0 + 120])
ps2 = A([101.0, 99.0, 99.0])
seen = F.run_levels(prior, ts2)
side_old = F._side(prior[0], ts2, ps2, F.Tree(list(ps2)))
side_new = F._side(seen[0], ts2, ps2, F.Tree(list(ps2)))
t('SH2: a run that starts after the session opened sees yesterday\'s POC, '
  'VAH and VAL from its first mid (one starting after the run ended is '
  'dropped), so they can break there; before, they never could',
  seen == [(T0, 100.0, 'POC'), (T0, 102.0, 'VAH')] and
  side_old == (None, 0) and side_new == (0, -1))


# ---------------------------------------------------------------------
# SH3: HELD must still be beyond the level at its entry (finding 2)
# ---------------------------------------------------------------------
def mkpath(pts):
    ts, ps = A([a for a, _ in pts]), A([b for _, b in pts])
    return ts, ps, F.Tree(list(ps))


def mkgrid(rows, t0=T0):
    g = [dict(t=t0 + dt, D=D, z_delta_s=z, resp=r, mid=m, D60=d60,
              w7_lv=(None,) * 7) for dt, D, z, r, m, d60 in sorted(rows)]
    return g, [x['t'] for x in g]


LV = (T0, 100.0, 'SWING_H')
rows = [(dt, 20, 1.0, 1.0, 100.75, 30) for dt in range(10, 900, 10)
        if dt not in (180, 190)] + [(195, 60, 2.4, 2.0, 101.0, 60)]
gH, gtH = mkgrid(rows)


def held_path(dip):
    return mkpath([(T0, 99.0), (T0 + 60, 100.5), (T0 + 100, 101.0),
                   (T0 + 185, dip), (T0 + 195, 101.0), (T0 + 300, 112.0),
                   (T0 + 900, 125.0)])


ev_back = F.detect(LV, held_path(99.5), gH, gtH)
ev_kept = F.detect(LV, held_path(100.0), gH, gtH)
t('SH3: HELD: back a tick through the level after the 120 s but before '
  'its entry tick (185 s, entry 195 s): no trade; a dip that stays above '
  'that tick still enters at 195 s',
  ev_back is None and ev_kept is not None and ev_kept['kind'] == 'HELD'
  and ev_kept['t_entry'] == T0 + 195)


# ---------------------------------------------------------------------
# SH4: a WICK window that runs out on the far side (finding 3)
# ---------------------------------------------------------------------
def mkgrid_e(spec):
    lv = tuple(100.0 if k == 'YDAY_HIGH' else None for k in E.FIXED_IDS)
    return [dict(t=float(tt), instrument='NQ', session='20260902', run='r1',
                 mid=m, D=D, z_delta_s=z, w11_lv=lv)
            for tt, (m, D, z) in sorted(spec.items())]


spec = {tt: (99.0, 0.0, None) for tt in range(600, 1500, 10)}
spec[660] = (100.5, 10.0, 0.5)                      # up through at 660
for tt in range(670, 970, 10):
    spec[tt] = (100.5, 5.0, 0.5)                    # stays up, no flip
spec[970] = (99.5, 5.0, 0.5)                        # window over, below
spec[980] = (100.5, 20.0, 1.5)                      # back up, buyers
for tt in range(990, 1500, 10):
    spec[tt] = (100.5, 5.0, 0.5)
gw = mkgrid_e(spec)
got = E.run_episodes(gw, {int(g['t']): g for g in gw}, [],
                     {'20260902': 0}, collections.Counter(), 'WICK')
t('SH4: WICK: the close that ends a 300 s window on the far side of the '
  'level starts the next break there (test 2), as EARLY and CLOSE do; '
  'the reclaim with flow 10 s later is its trade',
  [(e['t'], e['direction'], e['test_no']) for e in got] ==
  [(980.0, 1, 2)])

# ---------------------------------------------------------------------
# SH5: one value-area lookup per session (finding 4)
# ---------------------------------------------------------------------
T930 = float(calendar.timegm((2026, 9, 2, 13, 30, 0)))
fast = {dt: (105.0, 0.0, None) for dt in range(0, 400, 10)}
fast.update({100: (112.0, 5.0, 0.5), 110: (113.0, 5.0, 0.5),
             120: (113.0, 5.0, 0.5), 130: (112.5, -10.0, 1.0),
             140: (109.0, -30.0, 2.5)})
grid5 = [dict(t=T930 + 86400 + 1800 + dt + off, instrument='NQ',
              session='20260903', run=run, mid=m, D=D, z_delta_s=z)
         for run, off in (('r1', 0), ('r2', 1200))
         for dt, (m, D, z) in sorted(fast.items())]
vals5 = {'NQ': {'20260902': (100.0, 110.0, 90.0)}}
calls = []
real_pv = VA.prev_value
VA.prev_value = lambda v, s: calls.append(s) or real_pv(v, s)
try:
    ev5 = VA.va_events(types.SimpleNamespace(grid=grid5, values=vals5))
finally:
    VA.prev_value = real_pv
t('SH5: yesterday\'s value area is looked up once per run and session, '
  'not on every 10 s tick, and the events are unchanged',
  calls == ['20260903', '20260903'] and len(grid5) == 80 and
  [(e['run'], e['t'] - T930 - 86400) for e in ev5] ==
  [('r1', 1940.0), ('r2', 3140.0)])

# ---------------------------------------------------------------------
# SH6: the Eastern offset is public (finding 5)
# ---------------------------------------------------------------------
probe = [float(calendar.timegm((2026, mo, d, h, mi, 0)))
         for mo, d in ((3, 8), (11, 1), (9, 2))
         for h in range(4, 9) for mi in (0, 30, 59)]
t('SH6: wave thirteen takes the Eastern second of day from wave eleven\'s '
  'public hourly offset, which agrees with the runner across both clock '
  'changes; no private helper of another wave is used',
  not hasattr(E, '_offset') and 'E._' not in SRC['mrofyt_valuearea'] and
  all(int((x + E.et_offset_hourly(x)) % 86400) == RUN.sod_seconds(x)
      for x in probe))

# ---------------------------------------------------------------------
# SH7: the compressed paths are built once per read (finding 7)
# ---------------------------------------------------------------------
series = {('NQ', 'r1'): (A([1.0, 2.0, 3.0, 4.0]), A([10.0, 10.0, 11.0, 11.0])),
          ('NQ', 'r2'): (A([]), A([])),
          ('MNQ', 'r1'): (A([1.0, 5.0]), A([20.0, 21.0]))}
rr = types.SimpleNamespace(series=series)
n_comp = []
real_c = BM.compress
BM.compress = lambda ts, ps: n_comp.append(1) or real_c(ts, ps)
try:
    p1 = V.compressed_paths(rr)
    p2 = V.compressed_paths(rr)
finally:
    BM.compress = real_c
t('SH7: every scorer shares one set of compressed paths per read: built '
  'once (empty runs left out), the same object on the next call, equal to '
  'compressing afresh; no wave compresses the full series itself',
  p1 is p2 and len(n_comp) == 2 and set(p1) == {('NQ', 'r1'),
                                                 ('MNQ', 'r1')} and
  all(p1[k] == real_c(*series[k]) for k in p1) and
  SRC['mrofyt_l2variants'].count('BM.compress(') == 1 and
  all('BM.compress(' not in SRC[n] for n in
      ('mrofyt_l2targets', 'mrofyt_closereclaim', 'mrofyt_earlylevels',
       'mrofyt_l2context', 'mrofyt_valuearea')))

# ---------------------------------------------------------------------
# SH8: wave eight winds back only the abandoned run's writes (finding 8)
# ---------------------------------------------------------------------
EMPTY = os.path.join(WORK, 'empty')
os.makedirs(EMPTY)
r8 = V.L2VariantRunner(EMPTY)
st = types.SimpleNamespace(instrument='NQ')
Ap = lambda i, lv: types.SimpleNamespace(id=i, level_id=lv)  # noqa: E731
for i, lv in ((1, 'YDAY_HIGH'), (2, 'YDAY_HIGH'), (3, 'ON_LOW')):
    r8._count_test(st, Ap(i, lv))
r8.tests_seen.clear()                              # a new session
before = (dict(r8.test_no), collections.Counter(r8.tests_seen))
real_m, real_u = LB.LevelBreakRunner._mark_run, LB.LevelBreakRunner._unwind_run
LB.LevelBreakRunner._mark_run = lambda self, s: {}
LB.LevelBreakRunner._unwind_run = lambda self, s, m: None
try:
    mark = r8._mark_run(st)
    for i, lv in ((4, 'ON_LOW'), (1, 'ON_LOW')):     # ids restart: 1 reused
        r8._count_test(st, Ap(i, lv))
    logged = len(mark['w8'][1])
    r8._unwind_run(st, mark)
finally:
    LB.LevelBreakRunner._mark_run, LB.LevelBreakRunner._unwind_run = \
        real_m, real_u
t('SH8: a mark keeps only the run\'s own writes (2, not the whole dict); '
  'unwinding restores an entry the run overwrote (approach numbers '
  'restart each session) and removes the ones it added',
  logged == 2 and r8.test_no == before[0] and before[0][('NQ', 1)] == 1 and
  list(r8.test_no) == list(before[0]) and r8.tests_seen == before[1])

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
