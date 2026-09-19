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


# ---------------------------------------------------------------------
# R12: disconnect gaps in OLD recordings are corrected retroactively.
# Recorder builds before the 2026-09-13 repair re-emitted BOOK_READY on
# the first depth row after a DISCONNECT (gate maxima were not reset with
# BookReady). That cleared DATA_SUPPRESSED on the rows that followed, so
# the runner re-armed and evaluated windows against a book the recorder
# had just declared invalid. Two things in those recordings are still
# correct and are what the runner now honours: every row inside the gap
# carries DISCONNECTED, and the spurious ready has no BOOK_RESYNC_START
# before it. The fixture below reproduces the old layout exactly.
# ---------------------------------------------------------------------
import hashlib                    # noqa: E402
import mles_v12_adapter as AD     # noqa: E402

T0 = E(2026, 9, 2, 13, 30)


def _gap_fixture(d, new_build):
    os.makedirs(d, exist_ok=True)
    cid, rid, ses, inst, con = 'gapcid', 'gapcid-R001', '20260902', 'NQ', \
        'NQ SEP26'
    com = 'MLES-CAPTURE-1.2,%s,%s,1,%s,%s,%s,' % (cid, rid, ses, inst, con)
    base = 'MLES12_NQ_NQ_SEP26_%s_%s' % (ses, rid)
    paths = {k: os.path.join(d, base + '_%s.csv' % k) for k in AD.STREAMS}
    fh = {k: open(paths[k], 'w') for k in AD.STREAMS}
    for k in AD.STREAMS:
        fh[k].write(','.join(AD.HEADERS[k]) + '\n')
    seq = [0]
    ss = dict(quotes=0, trades=0, depth=0, quality=0)
    clock = [T0]

    def row(k, stream, rest, dt_=0.01):
        clock[0] += dt_
        seq[0] += 1
        ss[k] += 1
        t = clock[0]
        fh[k].write(com + '%s,%d,%d,%s,%s,%d,%s\n'
                    % (stream, seq[0], ss[k], SY._iso(t), SY._iso(t - 0.25),
                       int((t - T0) * 1e7), rest))
        return t

    def q(kind, detail=''):
        return row('quality', 'QUALITY', '%s,%s' % (kind, detail))

    def book(flags):
        for l in range(10):
            row('depth', 'DEPTH', 'MBP,ADD,BID,%d,%.2f,10,%s'
                % (l, 15000 - 0.25 * l, flags))
            row('depth', 'DEPTH', 'MBP,ADD,ASK,%d,%.2f,9,%s'
                % (l, 15000.25 + 0.25 * l, flags))

    def quotes(n, flags):
        return [row('quotes', 'QUOTE',
                    'BID,15000.00,12,15000.00,12,15000.25,9,%s' % flags,
                    dt_=1.0) for _ in range(n)]

    q('SESSION_START', 'runId=' + rid)
    q('BOOK_RESYNC_START', 'declaredDepth=10')
    book('DATA_SUPPRESSED')
    q('BOOK_READY', 'bidLevels=10 askLevels=10')
    pre = quotes(5, '')
    t_disc = q('DISCONNECT', 'seg=1 book invalidated')
    if new_build:
        q('BOOK_RESYNC_START', 'declaredDepth=10')
        row('depth', 'DEPTH', 'MBP,UPDATE,BID,0,15000.00,7,'
            'DISCONNECTED|DATA_SUPPRESSED')
        gap = quotes(5, 'DISCONNECTED|DATA_SUPPRESSED')
    else:
        # OLD build: the depth row re-satisfies the gate -> spurious
        # ready -> BookReady true -> later rows lose DATA_SUPPRESSED
        row('depth', 'DEPTH', 'MBP,UPDATE,BID,0,15000.00,7,'
            'DISCONNECTED|DATA_SUPPRESSED')
        q('BOOK_READY', 'bidLevels=10 askLevels=10')       # spurious
        gap = quotes(5, 'DISCONNECTED')
    t_recon = q('RECONNECT', 'seg=2')
    q('BOOK_RESYNC_START', 'declaredDepth=10')
    book('DATA_SUPPRESSED')
    q('BOOK_READY', 'bidLevels=10 askLevels=10')
    post = quotes(5, '')
    t_end = q('SHUTDOWN', 'orderly')
    for k in AD.STREAMS:
        fh[k].close()
    man = dict(schema='MLES-CAPTURE-1.2', captureInstanceId=cid, runId=rid,
               session=ses, instrument=inst, contract=con,
               recorderBuild='1.2.1', closeReason='SHUTDOWN',
               firstRecvUtc=SY._iso(T0), lastRecvUtc=SY._iso(t_end),
               firstEventSeq=1, lastEventSeq=seq[0], declaredDepth=10)
    for k in AD.STREAMS:
        man[k] = dict(present=True, file=os.path.basename(paths[k]),
                      rows=ss[k], bytes=os.path.getsize(paths[k]),
                      sha256=hashlib.sha256(
                          open(paths[k], 'rb').read()).hexdigest())
    json.dump(man, open(os.path.join(d, base + '_manifest.json'), 'w'))
    return dict(pre=pre, gap=gap, post=post, t_disc=t_disc,
                t_recon=t_recon)


class _MidSpy(RN.Runner):
    def __init__(self, *a, **kw):
        RN.Runner.__init__(self, *a, **kw)
        self.seen = []                          # (t, st.ready)

    def _on_mid(self, st, t, mid):
        self.seen.append((t, st.ready))
        RN.Runner._on_mid(self, st, t, mid)


d12 = os.path.join(WORK, 'r12_old')
fx = _gap_fixture(d12, new_build=False)
r12 = _MidSpy(d12)
led12 = r12.run()
in_gap = [x for x in r12.seen if fx['t_disc'] <= x[0] <= fx['t_recon']]
before = [x for x in r12.seen if x[0] < fx['t_disc']]
after = [x for x in r12.seen if x[0] > fx['t_recon']]
t('R12: OLD-build gap -- the spurious BOOK_READY (no resync before it) '
  'does NOT re-arm and is counted; every DISCONNECTED row is suppressed; '
  'no mid inside the gap reaches the runner',
  led12['totals']['spurious_book_ready_ignored'] == 1 and
  led12['totals']['rows_disconnected_suppressed'] == 6 and
  not in_gap and len(before) == 5 and all(rd for _, rd in before))
t('R12b: after the genuine RECONNECT -> BOOK_RESYNC_START -> BOOK_READY '
  'the runner re-arms and post-gap mids are processed with ready=True',
  len(after) == 5 and all(rd for _, rd in after))

d12n = os.path.join(WORK, 'r12_new')
fxn = _gap_fixture(d12n, new_build=True)
r12n = _MidSpy(d12n)
led12n = r12n.run()
in_gap_n = [x for x in r12n.seen if fxn['t_disc'] <= x[0] <= fxn['t_recon']]
after_n = [x for x in r12n.seen if x[0] > fxn['t_recon']]
t('R12c: NEW-build gap (resync at BOTH disconnect and reconnect, no '
  'spurious ready) -- nothing is counted as spurious, the gap is still '
  'suppressed, and the post-reconnect ready re-arms',
  led12n['totals']['spurious_book_ready_ignored'] == 0 and
  not in_gap_n and len(after_n) == 5 and all(rd for _, rd in after_n))
t('R12d: summary reports the two book-integrity counters',
  'spurious BOOK_READY ignored=1' in RN.summary(led12) and
  'suppressed=6' in RN.summary(led12))


# ---------------------------------------------------------------------
# R13: a truncated or corrupt stream never crashes the runner and is
# never partially ingested.
#
# Found on real capture 2026-09-19: two DEC26 files copied while the
# recorder was still writing them ended mid-row, and the adapter raised
#     MalformedHeaderError: ...: expected 20 columns, got N
# from INSIDE the merge loop. The runner had exactly two except clauses
# in the whole module, both in plan(), so the exception escaped and the
# entire multi-hour pass died with no ledger written at all.
#
# Why a mid-stream skip is not enough on its own: the four streams are
# merged in eventSeq order, so a depth file that stops early while
# quotes keep going leaves the book frozen at the truncation point and
# every feature after it is computed against a stale book. So the size
# check must run BEFORE ingest (R13), and the exception handler exists
# only for corruption that leaves the byte count unchanged (R13b).
# ---------------------------------------------------------------------
d13 = os.path.join(WORK, 'trunc')
mp13 = SY.synth_run(d13, n_depth=40000, price_path=path, trade_every=10,
                    quote_every=5, cid='trunc', session='20260902')
man13 = json.load(open(mp13))
dp13 = os.path.join(d13, man13['depth']['file'])
with open(dp13, 'r+') as _fh:                 # lop off the tail
    _fh.truncate(man13['depth']['bytes'] - 5000)
led13 = RN.Runner(d13, ('NQ',)).run()
t('R13: a file smaller than its own manifest declares is caught by the '
  'stat() pre-flight and the run is skipped WHOLE, before any event of '
  'it is ingested',
  led13['totals'].get('runs_skipped_truncated') == 1 and
  led13['totals'].get('events', 0) == 0 and
  len(led13['skipped_runs']) == 1 and
  'truncated' in led13['skipped_runs'][0])

t('R13a: the skip names the file and both byte counts, so the operator '
  'can tell a truncated copy from a corrupt recording',
  man13['depth']['file'] in led13['skipped_runs'][0]['truncated'][0] and
  'manifest declares' in led13['skipped_runs'][0]['truncated'][0])

# corruption that does NOT change the byte count: overwrite a row in
# place with one that has too few columns. The pre-flight cannot see
# this, so the exception handler has to.
d13b = os.path.join(WORK, 'corrupt')
mp13b = SY.synth_run(d13b, n_depth=40000, price_path=path, trade_every=10,
                     quote_every=5, cid='corrupt', session='20260902')
man13b = json.load(open(mp13b))
dp13b = os.path.join(d13b, man13b['depth']['file'])
_rows = open(dp13b).read().splitlines(True)
_bad = len(_rows) // 2
_orig = _rows[_bad]
_rows[_bad] = ',' * 3 + ' ' * (len(_orig) - 4) + '\n'   # same byte length
assert len(''.join(_rows)) == man13b['depth']['bytes']
open(dp13b, 'w').writelines(_rows)
led13b = RN.Runner(d13b, ('NQ',)).run()
t('R13b: a corrupt row that leaves the byte count unchanged raises from '
  'inside the merge loop, is CAUGHT, and the run is reported skipped '
  'instead of killing the whole pass',
  led13b['totals'].get('runs_skipped_corrupt') == 1 and
  led13b['totals'].get('events', 0) == 0 and
  'corrupt' in led13b['skipped_runs'][0] and
  'columns' in led13b['skipped_runs'][0]['corrupt'])

t('R13c: neither skip contributes events, windows or fires -- a partly '
  'read run leaves nothing behind',
  led13b['totals'].get('windows', 0) == 0 and
  led13b['totals'].get('fires', 0) == 0 and
  led13['totals'].get('windows', 0) == 0)

t('R13d: the summary reports the three skip reasons separately, so '
  '"skipped" never hides which kind of problem the capture has',
  'missing-files' in RN.summary(led13) and
  'truncated 1' in RN.summary(led13) and
  'corrupt 1' in RN.summary(led13b))

# a clean run in the same folder must still be ingested normally
d13e = os.path.join(WORK, 'mixed')
SY.synth_run(d13e, n_depth=40000, price_path=path, trade_every=10,
             quote_every=5, cid='good', session='20260902')
mpx = SY.synth_run(d13e, n_depth=40000, price_path=path, trade_every=10,
                   quote_every=5, cid='bad', session='20260902', run_no=2)
manx = json.load(open(mpx))
dpx = os.path.join(d13e, manx['depth']['file'])
with open(dpx, 'r+') as _fh:
    _fh.truncate(manx['depth']['bytes'] - 5000)
led13e = RN.Runner(d13e, ('NQ',)).run()
t('R13e: one bad run does not poison the folder -- the clean run beside '
  'it is still ingested in full',
  led13e['totals'].get('runs_skipped_truncated') == 1 and
  led13e['totals'].get('events', 0) > 0 and
  sum(1 for r in led13e['runs'] if not r.get('skipped')) == 1)


# ---------------------------------------------------------------------
# R13f-R13i: the two holes the 2026-09-19 guards still had.
#
# R13b only ever exercised ONE flavour of same-size corruption: a row
# with the wrong column count, which the adapter reports as
# MalformedHeaderError. The handler caught that pair of adapter
# exceptions and nothing else -- but the adapter's numeric and timestamp
# primitives raise a BARE ValueError, so a row that keeps all twenty
# columns and garbles a price, a sequence number or a timestamp went
# straight past the handler and killed the pass, which is the failure
# the handler exists to prevent. And a run abandoned mid-stream left its
# prefix's windows, states and latency samples in a ledger that reports
# the run as never read; R13c missed it only because its bad row sits
# halfway through the file, before the first window completes.
# ---------------------------------------------------------------------
def _same_size_corrupt(tag, col, cell):
    """One depth cell rewritten in place, byte count unchanged."""
    d = os.path.join(WORK, tag)
    mp = SY.synth_run(d, n_depth=40000, price_path=path, trade_every=10,
                      quote_every=5, cid=tag, session='20260902')
    man = json.load(open(mp))
    dp = os.path.join(d, man['depth']['file'])
    rows = open(dp).read().splitlines(True)
    bad = len(rows) // 2
    cells = rows[bad].rstrip('\n').split(',')
    cells[col] = cell(cells[col])
    rows[bad] = ','.join(cells) + '\n'
    assert len(''.join(rows)) == man['depth']['bytes'], tag
    open(dp, 'w').writelines(rows)
    return man, RN.Runner(d, ('NQ',)).run()


_flavours = [
    ('px', 17, lambda v: v[:-1] + 'x'),          # float() ValueError
    ('seq', 8, lambda v: v[:-1] + 'O'),          # int() ValueError
    ('ts', 10, lambda v: 'X' * len(v)),          # parse_iso ValueError
]
_led13f = dict((tag, _same_size_corrupt(tag, col, fn))
               for tag, col, fn in _flavours)
t('R13f: same-byte-count corruption that keeps all 20 columns -- a '
  'garbled price, sequence number or timestamp -- is caught and skipped '
  'too, not just a wrong column count',
  all(led['totals'].get('runs_skipped_corrupt') == 1 and
      led['totals'].get('events', 0) == 0 and
      len(led['skipped_runs']) == 1
      for _man, led in _led13f.values()))

t('R13g: the skip names the file and how far the stream decoded, so the '
  'operator can find the bad row in a 25M-row file',
  all(man['depth']['file'] in led['skipped_runs'][0]['corrupt'] and
      'decoded rows' in led['skipped_runs'][0]['corrupt']
      for man, led in _led13f.values()))

# A truncation that lands exactly on a row boundary is the quiet one:
# every row that remains decodes perfectly, so NOTHING inside the merge
# can see it. Only the manifest's byte count can.
d13h = os.path.join(WORK, 'rowtrunc')
mp13h = SY.synth_run(d13h, n_depth=40000, price_path=path, trade_every=10,
                     quote_every=5, cid='rowtrunc', session='20260902')
man13h = json.load(open(mp13h))
dp13h = os.path.join(d13h, man13h['depth']['file'])
_rows13h = open(dp13h).read().splitlines(True)
open(dp13h, 'w').writelines(_rows13h[:-100])        # whole rows only
_decodes_clean = True
try:
    for _ in RN.AD.iter_file(dp13h, 'depth', True):
        pass
except ValueError:
    _decodes_clean = False
led13h = RN.Runner(d13h, ('NQ',)).run()
t('R13h: a truncation on an exact row boundary leaves a file that parses '
  'perfectly and is still short -- the pre-flight is the only guard that '
  'can see it, and it does',
  _decodes_clean and
  led13h['totals'].get('runs_skipped_truncated') == 1 and
  led13h['totals'].get('events', 0) == 0)

# The prefix of an abandoned run must leave NOTHING behind. Corrupt a
# row at 90% of the file, where the same fixture run clean records
# windows, wall states and 46k latency samples.
d13i = os.path.join(WORK, 'clean_ref')
SY.synth_run(d13i, n_depth=40000, price_path=path, trade_every=10,
             quote_every=5, cid='clean_ref', session='20260902')
led_clean = RN.Runner(d13i, ('NQ',)).run()
d13j = os.path.join(WORK, 'late')
mp13j = SY.synth_run(d13j, n_depth=40000, price_path=path, trade_every=10,
                     quote_every=5, cid='late', session='20260902')
man13j = json.load(open(mp13j))
dp13j = os.path.join(d13j, man13j['depth']['file'])
_rows13j = open(dp13j).read().splitlines(True)
_late = int(len(_rows13j) * 0.9)
_orig13j = _rows13j[_late]
_rows13j[_late] = ',' * 3 + ' ' * (len(_orig13j) - 4) + '\n'
assert len(''.join(_rows13j)) == man13j['depth']['bytes']
open(dp13j, 'w').writelines(_rows13j)
led13j = RN.Runner(d13j, ('NQ',)).run()
t('R13i: a run abandoned LATE is wound back whole -- the windows, wall '
  'states, latency samples and open approaches its prefix produced are '
  'gone from a ledger that reports events=0 (the clean fixture records '
  'all of them, so this is not vacuous)',
  led_clean['totals']['windows'] > 0 and
  led_clean['latency_ms']['NQ']['n'] > 0 and
  led_clean['totals']['approaches'] > 0 and
  led13j['totals'].get('runs_skipped_corrupt') == 1 and
  led13j['totals'].get('windows', 0) == 0 and
  led13j['totals'].get('approaches', 0) == 0 and
  led13j['totals'].get('windows_incomplete_at_close', 0) == 0 and
  led13j['latency_ms']['NQ']['n'] == 0 and
  not led13j['fires'] and not led13j['states'] and
  not led13j['feature_none'])

# The guard wraps the DECODING of a row and nothing else. A ValueError
# from the runner's own per-event work must still propagate as the bug
# it is, or a detector fault would be filed as a corrupt recording and
# the capture blamed for it.


class _BrokenRunner(RN.Runner):
    def _on_mid(self, st, t, mid):
        raise ValueError('detector bug, not a corrupt capture')


_own_bug_escapes = False
try:
    _BrokenRunner(d13i, ('NQ',)).run()
except ValueError as _exc:
    _own_bug_escapes = 'detector bug' in str(_exc)
t('R13j: the guard covers row decoding only -- a ValueError raised by '
  "the runner's own per-event work still propagates instead of being "
  'reported as a corrupt stream',
  _own_bug_escapes)


shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
