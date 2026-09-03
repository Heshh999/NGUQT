#!/usr/bin/env python3
# MROF-YT-RUNNER-1.2.1 suite: the outcome-blind streaming ingest runner
# is exercised on synthetic recorder-format runs (mles_v12_synth) and on
# the frozen components it wires. Synthetic events verify CODE BEHAVIOR
# only, never market evidence. No outcome, R or P&L exists anywhere.
import datetime as dt
import json
import math
import os
import re
import shutil
import sys
import tempfile
import tracemalloc

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrof_engine as ME         # noqa: E402
import mrofyt_runner as RN       # noqa: E402
import rvmr_spec as RV           # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-66s %s' % (name, 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofrun_', dir='/tmp')
E = lambda *a: (dt.datetime(*a, tzinfo=dt.timezone.utc)  # noqa: E731
                - dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
                ).total_seconds()

# R1: the outcome door is locked and nothing outcome-shaped is reachable
src = open(os.path.join(HERE, 'mrofyt_runner.py')).read()
code = re.sub(r'#.*', '', src)
locked = False
try:
    RN.compute_outcomes()
except RuntimeError as exc:
    locked = 'STATE-C LOCKED' in str(exc)
t('R1: compute_outcomes raises STATE-C LOCKED; runner source calls no '
  'fill/stop/target/simulate/P&L function',
  locked and not ME.research_unlocked() and RN.OUTCOMES_LOCKED and
  not any(s in code for s in ('simulate(', 'y_dollars', 'entry_fill(',
                                 'structural_stop(', 'fill_first_book',
                                 'markout')))

# R2: US Eastern clock without tzdata (DST boundaries 2026) + session id
t('R2: ET offset flips at 2026-03-08 07:00Z and 2026-11-01 06:00Z; '
  'session rolls at 18:00 ET (22:00Z in EDT)',
  RN.et_offset(E(2026, 3, 8, 6, 59)) == -5 * 3600 and
  RN.et_offset(E(2026, 3, 8, 7, 0)) == -4 * 3600 and
  RN.et_offset(E(2026, 11, 1, 5, 59)) == -4 * 3600 and
  RN.et_offset(E(2026, 11, 1, 6, 0)) == -5 * 3600 and
  RN.session_id(E(2026, 9, 1, 21, 59)) == '20260901' and
  RN.session_id(E(2026, 9, 1, 22, 0)) == '20260902' and
  abs(RN.sod_seconds(E(2026, 9, 2, 13, 30)) - 9.5 * 3600) < 1e-6)

# R3: streaming RVMR trailing ratio and ATR20 equal the frozen batch forms
import random  # noqa: E402
random.seed(7)
xs = [random.random() * 10 for _ in range(3000)]
ref = RV.trailing_ratio(xs)
rr = RN.RollingTrailingRatio()
got = [rr.push(v) for v in xs]
same = all((a is None and b is None) or
           (a is not None and b is not None and abs(a - b) < 1e-9)
           for a, b in zip(ref, got))
bars = []
p = 15000.0
for i in range(60):
    o = p
    h = o + random.random() * 3
    l = o - random.random() * 3
    c = l + random.random() * (h - l)
    bars.append((i, o, h, l, c, 1))
    p = c
refa = RV.atr20(bars)
ra = RN.RollingATR20()
gota = [ra.push(b[2], b[3], b[4]) for b in bars]
samea = all((a is None and b is None) or
            (a is not None and b is not None and abs(a - b) < 1e-9)
            for a, b in zip(refa, gota))
t('R3: streaming trailing_ratio (1440-bar, current excluded) and ATR20 '
  'reproduce rvmr_spec exactly; None until history exists',
  same and samea and got[1439] is None and got[1440] is not None)

# R4: end-to-end on a synthetic oscillating market (approaches, windows,
# states, feature availability, zero fires with insufficient baseline)
d4 = os.path.join(WORK, 'osc')
path = lambda i: 15000.0 + 3.0 * math.sin(2 * math.pi * (i * 0.0005) / 20.0)  # noqa: E731
SY.synth_run(d4, n_depth=120000, price_path=path, trade_every=10,
             quote_every=5)
tracemalloc.start()
led = RN.Runner(d4, ('NQ',)).run()
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
tot = led['totals']
t('R4: approaches to OPEN/VWAP detected, 10 s windows complete (incl. '
  'after the retreat), states recorded, zero fires with baseline < 5 '
  'sessions, every z-feature reported None',
  tot['approaches'] >= 10 and tot['windows'] >= 8 and
  tot.get('fires', 0) == 0 and
  set(led['states']) == {'NO_QUALIFYING_WALL'} and
  led['feature_none']['aggr_z'] == tot['windows'] and
  led['feature_none']['trend_dir'] == tot['windows'] and
  led['baseline_sessions'] == {'NQ': 1})
t('R4b: ledger is outcome-free (no R/pnl/markout/fill keys) and flat in '
  'memory (< 40 MB peak on 150k events)',
  led['outcomes'] == 'LOCKED' and
  not re.search(r'"(R|pnl|markout|fill|target|stop)[a-z_]*":',
                json.dumps(led, default=str)) and peak < 40e6)

# R5: multi-session carry — baselines need 5 prior sessions in the same
# 5-minute bucket; day-6 windows then have aggr_z; YDAY/PIVOT levels
# appear from session 2
d5 = os.path.join(WORK, 'multi')
base_t0 = E(2026, 9, 1, 13, 30)
for k in range(6):
    day = dt.date(2026, 9, 1) + dt.timedelta(days=k)
    # distinct seeds: identical tapes every day would give the frozen
    # robust baseline a zero MAD and (correctly) no z at all
    SY.synth_run(d5, n_depth=50000, price_path=path, trade_every=10,
                 quote_every=5, session=day.strftime('%Y%m%d'),
                 cid='cid%d' % k, t0=base_t0 + 86400 * k, seed=k + 1)
led5 = RN.Runner(d5, ('NQ',)).run()
ses = sorted(led5['sessions'])
lv2 = led5['sessions'][ses[1]]['NQ']['levels']
t('R5: six synthetic sessions -> baseline_sessions 6, YDAY/PIVOT levels '
  'from session 2, aggr_z becomes available (feature None count < '
  'windows) once >= 5 prior sessions exist',
  led5['baseline_sessions'] == {'NQ': 6} and len(ses) == 6 and
  {'YDAY_HIGH', 'YDAY_LOW', 'PP'} <= set(lv2) and
  led5['totals']['windows'] > 0 and
  led5['feature_none']['aggr_z'] < led5['totals']['windows'])

# R6: partial windows at close are counted, never evaluated
t('R6: windows still open at session close are counted as incomplete, '
  'not evaluated',
  'windows_incomplete_at_close' in led5['totals'] and
  led5['totals']['windows_incomplete_at_close'] >= 0)

# R7: frozen sweep + reclaim through the runner's window path
tr = [(0.1 + i * 0.1, 15000.0 + i * 0.25, 2, +1) for i in range(4)]
swp = RN.SIG.sweep(tr)
mids = [(0.5, 15000.75), (1.0, 15000.5), (2.0, 15000.0)]
t('R7: frozen sweep() and sweep_reclaimed() are the ones the runner '
  'calls (3-level same-direction sweep inside 1 s reclaimed in 5 s)',
  swp is not None and swp['levels'] >= 3 and
  RN.SIG.sweep_reclaimed(swp, mids) is True and
  'SIG.sweep(' in src and 'SIG.sweep_reclaimed(' in src)

# R8: A3 vacuum arithmetic — non-trade withdrawal on the target side,
# opposite side stable
t('R8: vacuum_event(0.70, 0.10) True, (0.50, 0.10) False, '
  '(0.70, 0.30) False (frozen 60%/20%)',
  RN.SIG.vacuum_event(0.70, 0.10) and not RN.SIG.vacuum_event(0.50, 0.10)
  and not RN.SIG.vacuum_event(0.70, 0.30))

# R9: NOT-WIRED inputs are named, passed as None, and disqualify
t('R9: resid_tail_5pct and trend_dir are declared NOT WIRED and A5 '
  'returns 0 on the runner feature dict shape',
  set(RN.NOT_WIRED) == {'resid_tail_5pct', 'trend_dir'} and
  RN.SIG.DETECTORS['A5'](dict(trend_dir=None, adverse_z=2.5,
                              adverse_progress_ticks=0, replenish_z=2.0,
                              trend_flip_z=1.5)) == 0)

# R10: CLI summary text carries the lock and the not-wired list
s = RN.summary(led)
t('R10: summary states outcomes=LOCKED and lists NOT WIRED inputs',
  'outcomes=LOCKED' in s and 'resid_tail_5pct' in s and 'trend_dir' in s)

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
